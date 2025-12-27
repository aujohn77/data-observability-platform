# ============================================
# jobs/run_anomaly_detection.py (orchestrator)
# Status vocabulary: started / succeeded / failed
# Runs detectors in a loop (modular)
# ============================================

import os
import time
import traceback
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

from jobs.anomaly_detectors import silent_station, stale_data, spike, drop, flatline


load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

JOB_NAME = "anomaly_detection"

# --- anomaly insert ---
SQL_INSERT_ANOMALY = """
insert into public.ops_anomaly
  (anomaly_type, station_id, metric_id, severity, details, detected_at, detected_hour)
values
  (%s, %s, %s, %s, %s, now(), date_trunc('hour', now()))
on conflict on constraint uq_ops_anomaly_dedup do nothing;
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

def insert_anomalies(conn, rows) -> int:
    inserted = 0
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
            inserted += cur.rowcount
    return inserted

def run_one_detector(conn, run_id, detector_name, detect_fn) -> None:
    """
    Runs one detector with:
    - detector_run row (started -> succeeded/failed)
    - anomaly inserts + dedupe
    """
    detector_run_id = None
    t0 = time.time()

    try:
        # start detector run
        with conn.cursor() as cur:
            cur.execute(SQL_CREATE_DETECTOR_RUN, (run_id, detector_name))
            detector_run_id = cur.fetchone()[0]
        conn.commit()

        # detect + insert
        rows = detect_fn(conn)
        rows_detected = len(rows)

        rows_inserted = 0
        if rows:
            rows_inserted = insert_anomalies(conn, rows)
            conn.commit()

        duration_ms = int((time.time() - t0) * 1000)

        # finish detector run (success)
        with conn.cursor() as cur:
            cur.execute(
                SQL_FINISH_DETECTOR_RUN,
                ("succeeded", duration_ms, rows_detected, rows_inserted, None, detector_run_id),
            )
        conn.commit()

        print(f"{detector_name}: detected={rows_detected}, inserted={rows_inserted}")

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
