
import os
import time
import traceback

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

from jobs.anomaly_detectors import silent_station, stale_data, spike, drop, flatline


load_dotenv()
DATABASE_URL = os.environ["OBS_DATABASE_URL"]

JOB_NAME = "anomaly_detection"

# --- anomaly insert (RETURNING so we can link incident only for NEW rows) ---
SQL_INSERT_ANOMALY = """
insert into public.ops_anomaly
  (anomaly_type, station_id, metric_id, severity, details, detected_at, detected_hour)
values
  (%s, %s, %s, %s, %s, now(), date_trunc('hour', now()))
on conflict on constraint uq_ops_anomaly_dedup do nothing
returning anomaly_id, anomaly_type, station_id, metric_id, severity, details, detected_at;
"""

# --- incident upsert + link ---
SQL_GET_OR_CREATE_INCIDENT = """
with existing as (
  select incident_id
  from public.ops_incident
  where status in ('open','acknowledged')
    and anomaly_type = %s
    and station_id = %s
    and coalesce(metric_id, -1) = coalesce(%s, -1)
  order by created_at desc
  limit 1
),
ins as (
  insert into public.ops_incident
    (status, severity, anomaly_type, station_id, metric_id, created_at, last_seen_at, title, details)
  select
    'open',
    %s,
    %s,
    %s,
    %s,
    now(),
    now(),
    %s,
    %s
  where not exists (select 1 from existing)
  returning incident_id
)
select incident_id from ins
union all
select incident_id from existing;
"""

SQL_TOUCH_INCIDENT = """
update public.ops_incident
set last_seen_at = now()
where incident_id = %s;
"""

SQL_LINK_INCIDENT_ANOMALY = """
insert into public.ops_incident_anomaly (incident_id, anomaly_id)
values (%s, %s)
on conflict do nothing;
"""

# --- ops_job_run ---
SQL_CREATE_JOB_RUN = """
insert into public.ops_job_run (job_name, status, started_at)
values (%s, 'started', now())
returning run_id;
"""

SQL_FINISH_JOB_RUN = """
update public.ops_job_run
set status = %s,
    ended_at = now(),
    error_message = %s
where run_id = %s;
"""

# --- ops_anomaly_detector_run ---
SQL_CREATE_DETECTOR_RUN = """
insert into public.ops_anomaly_detector_run
  (run_id, detector_name, status, started_at)
values
  (%s, %s, 'started', now())
returning detector_run_id;
"""

SQL_FINISH_DETECTOR_RUN = """
update public.ops_anomaly_detector_run
set status = %s,
    finished_at = now(),
    duration_ms = %s,
    rows_detected = %s,
    rows_inserted = %s,
    error_message = %s
where detector_run_id = %s;
"""


def insert_anomalies(conn, rows) -> list[dict]:
    """
    Insert anomalies with hourly dedupe.
    Returns ONLY the anomalies that were actually inserted (not deduped),
    including anomaly_id for incident linking.
    """
    inserted_rows: list[dict] = []
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(
                SQL_INSERT_ANOMALY,
                (
                    r["anomaly_type"],
                    r["station_id"],
                    r["metric_id"],
                    r["severity"],
                    Json(r["details"]),
                ),
            )
            out = cur.fetchone()  # None if deduped (ON CONFLICT DO NOTHING)
            if out:
                inserted_rows.append(
                    {
                        "anomaly_id": out[0],
                        "anomaly_type": out[1],
                        "station_id": out[2],
                        "metric_id": out[3],
                        "severity": out[4],
                        "details": out[5],
                        "detected_at": out[6],
                    }
                )
    return inserted_rows


def upsert_incidents_for_new_anomalies(conn, inserted_anomalies: list[dict]) -> int:
    """
    For each NEW anomaly inserted (not deduped):
    - find existing open/ack incident for same (anomaly_type, station_id, metric_id)
      OR create a new one
    - link anomaly to incident
    - touch last_seen_at
    """
    linked = 0
    with conn.cursor() as cur:
        for a in inserted_anomalies:
            title = f"{a['anomaly_type']} @ station {a['station_id']} metric {a['metric_id']}"
            cur.execute(
                SQL_GET_OR_CREATE_INCIDENT,
                (
                    a["anomaly_type"],
                    a["station_id"],
                    a["metric_id"],
                    a["severity"],
                    a["anomaly_type"],
                    a["station_id"],
                    a["metric_id"],
                    title,
                    Json(a["details"]),
                ),
            )
            incident_id = cur.fetchone()[0]

            cur.execute(SQL_TOUCH_INCIDENT, (incident_id,))
            cur.execute(SQL_LINK_INCIDENT_ANOMALY, (incident_id, a["anomaly_id"]))
            linked += 1
    return linked


def run_one_detector(conn, run_id, detector_name, detect_fn) -> None:
    """
    Runs one detector with:
    - detector_run row (started -> succeeded/failed)
    - anomaly inserts + dedupe
    - Stage 9b: incident upsert + anomaly linking (only for NEW anomalies)
    """
    detector_run_id = None
    t0 = time.time()

    try:
        # start detector run
        with conn.cursor() as cur:
            cur.execute(SQL_CREATE_DETECTOR_RUN, (run_id, detector_name))
            detector_run_id = cur.fetchone()[0]
        conn.commit()

        # detect
        rows = detect_fn(conn)
        rows_detected = len(rows)

        # insert anomalies (RETURNING only newly inserted)
        inserted_anomalies: list[dict] = []
        if rows:
            inserted_anomalies = insert_anomalies(conn, rows)
            conn.commit()

        # create/link incidents ONLY for new anomalies
        linked_incidents = 0
        if inserted_anomalies:
            linked_incidents = upsert_incidents_for_new_anomalies(conn, inserted_anomalies)
            conn.commit()

        rows_inserted = len(inserted_anomalies)
        duration_ms = int((time.time() - t0) * 1000)

        # finish detector run (success)
        with conn.cursor() as cur:
            cur.execute(
                SQL_FINISH_DETECTOR_RUN,
                ("succeeded", duration_ms, rows_detected, rows_inserted, None, detector_run_id),
            )
        conn.commit()

        print(
            f"{detector_name}: detected={rows_detected}, "
            f"inserted={rows_inserted}, linked_incidents={linked_incidents}"
        )

    except Exception as e:
        conn.rollback()  # clear aborted tx state

        duration_ms = int((time.time() - t0) * 1000)
        err = "".join(traceback.format_exception_only(type(e), e)).strip()

        # finish detector run (failed) IF we managed to create it
        if detector_run_id is not None:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_FINISH_DETECTOR_RUN,
                    ("failed", duration_ms, 0, 0, err, detector_run_id),
                )
            conn.commit()

        raise


def main():
    with psycopg2.connect(DATABASE_URL) as conn:
        # create job run
        with conn.cursor() as cur:
            cur.execute(SQL_CREATE_JOB_RUN, (JOB_NAME,))
            run_id = cur.fetchone()[0]
        conn.commit()

        job_status = "succeeded"
        job_error = None

        detectors = [
            ("silent_station", silent_station.detect),
            ("stale_data", stale_data.detect),
            ("spike", spike.detect),
            ("drop", drop.detect),
            ("flatline", flatline.detect),
        ]

        try:
            for detector_name, detect_fn in detectors:
                run_one_detector(conn, run_id, detector_name, detect_fn)

        except Exception as e:
            job_status = "failed"
            job_error = "".join(traceback.format_exception_only(type(e), e)).strip()
            raise

        finally:
            conn.rollback()  # safe guard
            with conn.cursor() as cur:
                cur.execute(SQL_FINISH_JOB_RUN, (job_status, job_error, run_id))
            conn.commit()

            print(f"Anomaly job finished. run_id={run_id} status={job_status}")


if __name__ == "__main__":
    main()
