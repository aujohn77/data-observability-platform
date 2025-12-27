import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

INGEST_JOB_NAME = "ingest_openmeteo_all_stations"
TRANSFORM_JOB_NAME = "transform_raw_to_fact"


def get_eligible_ingest_runs(cur):
    """
    Ingest runs that:
    - succeeded
    - have a succeeded transform child
    - do NOT yet have DQ results
    """
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
    passed = False

    if operator == "<=":
        passed = metric_value <= threshold
    elif operator == ">=":
        passed = metric_value >= threshold
    elif operator == "=":
        passed = metric_value == threshold

    if passed:
        return "pass"

    return "fail" if severity == "critical" else "warn"


def run_dq_for_run(cur, run_id):
    checks = load_active_checks(cur)

    for c in checks:
        cur.execute(c["check_sql_template"], {"run_id": run_id})

        row = cur.fetchone()
        metric_value = row["metric_value"] if isinstance(row, dict) else row[0]


        status = evaluate_status(
            metric_value,
            c["threshold_value"],
            c["threshold_operator"],
            c["severity"],
        )

        cur.execute(
            """
            insert into public.ops_dq_check_run
              (run_id, check_name, status, metric_value, threshold)
            values
              (%s, %s, %s, %s, %s)
            on conflict (run_id, check_name) do nothing;
            """,
            (
                run_id,
                c["check_name"],
                status,
                metric_value,
                c["threshold_value"],
            ),
        )


def main():
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            ingest_runs = get_eligible_ingest_runs(cur)

            if not ingest_runs:
                print("No eligible ingest runs for DQ.")
                return

            for run_id in ingest_runs:
                print(f"Running DQ for ingest run {run_id}")
                run_dq_for_run(cur, run_id)

        conn.commit()


if __name__ == "__main__":
    main()
