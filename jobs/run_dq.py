import os
import uuid
import traceback
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["OBS_DATABASE_URL"]

INGEST_JOB_NAME = "ingest_openmeteo_all_stations"
TRANSFORM_JOB_NAME = "transform_raw_to_fact"
DQ_JOB_NAME = "dq_check_run"


def utcnow():
    return datetime.now(timezone.utc)


def get_eligible_ingest_runs(cur):
    cur.execute(
        """
        select i.run_id
        from public.ops_job_run i
        where i.job_name = %s
          and i.status = 'succeeded'
          and exists (
              select 1
              from public.ops_job_run t
              where t.parent_run_id = i.run_id
                and t.job_name = %s
                and t.status = 'succeeded'
          )
          and not exists (
              select 1
              from public.ops_dq_check_run d
              where d.run_id = i.run_id
          )
        order by i.started_at;
        """,
        (INGEST_JOB_NAME, TRANSFORM_JOB_NAME),
    )
    return [r["run_id"] for r in cur.fetchall()]


def load_active_checks(cur):
    cur.execute(
        """
        select
          dq_check_id,
          check_name,
          threshold_value,
          threshold_operator,
          severity,
          check_sql_template
        from public.ops_dq_check_definition
        where is_active = true;
        """
    )
    return cur.fetchall()


def evaluate_status(metric_value, threshold, operator, severity):
    if operator == "<=":
        passed = metric_value <= threshold
    elif operator == ">=":
        passed = metric_value >= threshold
    elif operator == "=":
        passed = metric_value == threshold
    else:
        passed = False

    if passed:
        return "pass"
    return "fail" if severity == "critical" else "warn"


def start_job(cur, job_name, parent_run_id):
    cur.execute(
        """
        insert into public.ops_job_run
          (run_id, job_name, status, started_at, parent_run_id,
           rows_inserted, rows_updated, rows_deduped)
        values
          (%s, %s, 'started', %s, %s, 0, 0, 0)
        returning run_id;
        """,
        (str(uuid.uuid4()), job_name, utcnow(), parent_run_id),
    )
    return cur.fetchone()["run_id"]


def finish_job(cur, run_id, status, rows_inserted=0, error_message=None):
    cur.execute(
        """
        update public.ops_job_run
           set status = %s,
               ended_at = %s,
               rows_inserted = %s,
               error_message = %s
         where run_id = %s;
        """,
        (status, utcnow(), rows_inserted, error_message, run_id),
    )


def run_dq_for_ingest_run(cur, ingest_run_id):
    checks = load_active_checks(cur)
    inserted = 0

    for c in checks:
        # Run the check SQL
        cur.execute(c["check_sql_template"], {"run_id": ingest_run_id})
        row = cur.fetchone()

        metric_value = (
            row["metric_value"] if isinstance(row, dict) else row[0]
        )

        status = evaluate_status(
            metric_value,
            c["threshold_value"],
            c["threshold_operator"],
            c["severity"],
        )

        # INSERT WITH dq_check_id (FIX)
        cur.execute(
            """
            insert into public.ops_dq_check_run
              (dq_check_id, run_id, check_name, status, metric_value, threshold)
            values
              (%s, %s, %s, %s, %s, %s)
            on conflict (run_id, check_name) do nothing;
            """,
            (
                c["dq_check_id"],
                ingest_run_id,
                c["check_name"],
                status,
                metric_value,
                c["threshold_value"],
            ),
        )

        if cur.rowcount == 1:
            inserted += 1

    return inserted


def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            ingest_runs = get_eligible_ingest_runs(cur)

        if not ingest_runs:
            print("No eligible ingest runs for DQ.")
            return

        for ingest_run_id in ingest_runs:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                dq_run_id = start_job(cur, DQ_JOB_NAME, ingest_run_id)
                conn.commit()

            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    inserted = run_dq_for_ingest_run(cur, ingest_run_id)
                    finish_job(cur, dq_run_id, "succeeded", inserted)
                    conn.commit()

            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                tb = traceback.format_exc(limit=8)
                conn.rollback()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    finish_job(
                        cur,
                        dq_run_id,
                        "failed",
                        0,
                        err + "\n" + tb[:4000],
                    )
                    conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
