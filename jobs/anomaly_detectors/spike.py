# ============================================
# jobs/anomaly_detectors/spike.py
# Detector: spike (sudden upward jump vs previous reading)
# Hardcoded per-metric thresholds by metric_code
# ============================================

from psycopg2.extras import RealDictCursor, Json

# Hardcode thresholds per metric_code (edit these as you like)
# Units match your fact_observation.value_num units for that metric.
SPIKE_THRESHOLDS = {
    "air_temp_c": 5.0,      # +5°C jump
    "rel_hum_pct": 15.0,    # +15% RH jump
    "press_hpa": 8.0,       # +8 hPa jump
    "wind_spd_ms": 6.0,     # +6 m/s jump
    "wind_dir_deg": 90.0,   # +90° jump
    # add more metric_code thresholds if you have them
}

# Only compare if the two latest points are within this window (prevents “spike” after long gaps)
LOOKBACK_MINUTES = 180  # 3 hours

SQL_SPIKE = """
with ranked as (
  select
    f.station_id,
    f.metric_id,
    m.metric_code,
    f.observed_at,
    f.value_num,
    lag(f.value_num) over (partition by f.station_id, f.metric_id order by f.observed_at) as prev_value,
    lag(f.observed_at) over (partition by f.station_id, f.metric_id order by f.observed_at) as prev_observed_at
  from public.fact_observation f
  join public.dim_metric m
    on m.metric_id = f.metric_id
),
latest as (
  select
    r.*,
    row_number() over (partition by station_id, metric_id order by observed_at desc) as rn
  from ranked r
  where prev_value is not null
)
select
  'spike'::text as anomaly_type,
  s.station_id,
  l.metric_id,
  'medium'::text as severity,
  jsonb_build_object(
    'metric_code', l.metric_code,
    'last_observed_at', l.observed_at,
    'prev_observed_at', l.prev_observed_at,
    'last_value', l.value_num,
    'prev_value', l.prev_value,
    'delta', (l.value_num - l.prev_value),
    'threshold', (cfg.cfg ->> l.metric_code)::numeric,
    'lookback_minutes', %s
  ) as details
from latest l
join public.dim_station s
  on s.station_id = l.station_id
cross join (select %s::jsonb as cfg) cfg
where l.rn = 1
  and s.is_current = true
  and s.is_smoketest = false
  and l.prev_observed_at >= l.observed_at - (interval '1 minute' * %s)
  and (cfg.cfg ? l.metric_code)
  and (l.value_num - l.prev_value) > (cfg.cfg ->> l.metric_code)::numeric;
"""

def detect(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            SQL_SPIKE,
            (
                LOOKBACK_MINUTES,
                Json(SPIKE_THRESHOLDS),
                LOOKBACK_MINUTES,
            ),
        )
        return cur.fetchall()
