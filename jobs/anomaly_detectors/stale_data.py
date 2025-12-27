# ============================================
# jobs/anomaly_detectors/stale_data.py
# Detector: stale_data (no new data for a metric in N minutes)
# ============================================

from psycopg2.extras import RealDictCursor

STALE_MINUTES = 120  # change later if you want (2 hours)

SQL_STALE_DATA = """
with last_seen as (
  select
    station_id,
    metric_id,
    max(observed_at) as last_observed_at
  from public.fact_observation
  group by station_id, metric_id
)
select
  'stale_data'::text as anomaly_type,
  s.station_id,
  l.metric_id,
  'medium'::text as severity,
  jsonb_build_object(
    'last_observed_at', l.last_observed_at,
    'minutes_stale', round(extract(epoch from (now() - l.last_observed_at)) / 60.0, 2),
    'stale_threshold_minutes', %s
  ) as details
from last_seen l
join public.dim_station s
  on s.station_id = l.station_id
where s.is_current = true
  and s.is_smoketest = false
  and l.last_observed_at < now() - (interval '1 minute' * %s);
"""

def detect(conn) -> list[dict]:
    """
    Returns rows shaped like:
    {anomaly_type, station_id, metric_id, severity, details}
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SQL_STALE_DATA, (STALE_MINUTES, STALE_MINUTES))
        return cur.fetchall()
