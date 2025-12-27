# ============================================
# jobs/anomaly_detectors/silent_station.py
# Detector: silent_station (no data in 30 mins)
# ============================================

from psycopg2.extras import RealDictCursor

SQL_SILENT_STATION = """
with last_seen as (
  select
    station_id,
    max(observed_at) as last_observed_at
  from public.fact_observation
  group by station_id
)
select
  'silent_station'::text as anomaly_type,
  s.station_id,
  null::int as metric_id,
  'high'::text as severity,
  jsonb_build_object(
    'last_observed_at', l.last_observed_at,
    'minutes_silent',
      case
        when l.last_observed_at is null then null
        else round(extract(epoch from (now() - l.last_observed_at)) / 60.0, 2)
      end
  ) as details
from public.dim_station s
left join last_seen l
  on l.station_id = s.station_id
where s.is_current = true
  and s.is_smoketest = false
  and (l.last_observed_at is null
       or l.last_observed_at < now() - interval '30 minutes');
"""

def detect(conn) -> list[dict]:
    """
    Returns a list of anomaly rows shaped like:
    {anomaly_type, station_id, metric_id, severity, details}
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SQL_SILENT_STATION)
        return cur.fetchall()
