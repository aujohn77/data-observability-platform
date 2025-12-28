import os
import sys
import traceback

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["OBS_DATABASE_URL"]

INGEST_JOB_NAME = "ingest_openmeteo_all_stations"
TRANSFORM_JOB_NAME = "transform_raw_to_fact"

SQL_INSERT_ONE_RUN = """
insert into public.fact_observation
  (station_id, metric_id, observed_at, value_num, source, ingested_at, is_late, ingest_run_id)
select
  s.station_id,
  m.metric_id,
  r.observed_at,
  r.value_num,
  r.source,
  r.ingested_at,
  (r.ingested_at > r.observed_at + interval '24 hours') as is_late,
  r.ingest_run_id
from public.raw_observations r
join public.dim_station s
  on s.station_external_id = r.station_external_id
 and s.is_current = true
join public.dim_metric m
  on m.metric_code = r.metric_code
where r.value_num is not null
  and r.ingest_run_id = %s
on conflict (station_id, metric_id, observed_at)
do update set
  value_num     = excluded.value_num,
  source        = excluded.source,
  ingested_at   = excluded.ingested_at,
  is_late       = excluded.is_late,
  ingest_run_id = excluded.ingest_run_id;
"""

def start_job(cur, job_name: str, parent_run_id=None) -> str:
    cur.execute(
        """
        insert into public.ops_job_run
          (job_name, status, started_at, parent_run_id)
        values
          (%s, 'started', now(), %s)
        returning run_id
        """,
        (job_name, parent_run_id),
    )
    return cur.fetchone()[0]

def finish_job(cur, run_id: str, status: str, rows_upserted: int, error_message=None):
    cur.execute(
        """
        update public.ops_job_run
           set status = %s,
               ended_at = now(),
               rows_inserted = %s,
               error_message = %s
         where run_id = %s
        """,
        (status, rows_upserted, error_message, run_id),
    )

def get_pending_ingest_runs(cur):
    """
    Find all successful ingest runs that have NOT yet been transformed.
    """
    cur.execute(
        """
        select i.run_id
        from public.ops_job_run i
        left join public.ops_job_run t
          on t.parent_run_id = i.run_id
         and t.job_name = %s
        where i.job_name = %s
          and i.status = 'succeeded'
          and t.run_id is null
        order by i.started_at;
        """,
        (TRANSFORM_JOB_NAME, INGEST_JOB_NAME),
    )
    return [r[0] for r in cur.fetchall()]

def main() -> int:
    # Optional manual override
    run_id_arg = None
    if "--run-id" in sys.argv:
        i = sys.argv.index("--run-id")
        if i + 1 >= len(sys.argv):
            print("Missing value for --run-id", file=sys.stderr)
            return 2
        run_id_arg = sys.argv[i + 1]

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            if run_id_arg:
                ingest_run_ids = [run_id_arg]
            else:
                ingest_run_ids = get_pending_ingest_runs(cur)

        if not ingest_run_ids:
            print("No pending ingest runs to transform.")
            return 0

        for ingest_run_id in ingest_run_ids:
            with conn.cursor() as cur:
                transform_run_id = start_job(
                    cur,
                    TRANSFORM_JOB_NAME,
                    parent_run_id=ingest_run_id,
                )
                conn.commit()

            with conn.cursor() as cur:
                cur.execute(SQL_INSERT_ONE_RUN, (ingest_run_id,))
                affected = cur.rowcount or 0
                conn.commit()

            with conn.cursor() as cur:
                finish_job(cur, transform_run_id, "succeeded", affected)
                conn.commit()

        print("OK")
        return 0

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc(limit=8)
        try:
            conn.rollback()
            with conn.cursor() as cur:
                fail_run_id = start_job(cur, "transform_raw_to_fact_failed")
                finish_job(cur, fail_run_id, "failed", 0, err + "\n" + tb[:4000])
                conn.commit()
        except Exception:
            pass

        print(err, file=sys.stderr)
        print(tb, file=sys.stderr)
        return 1

    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
