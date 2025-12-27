# ============================================
# jobs/anomaly_detectors/flatline.py
# Detector: flatline (almost no variation over a window)
# Hardcoded per-metric "epsilon" (max-min <= epsilon)
# ============================================

from psycopg2.extras import RealDictCursor, Json

LOOKBACK_MINUTES = 180   # window to evaluate
MIN_POINTS = 6           # require at least N points in the window

# Epsilon per metric_code (units match value_num)
FLATLINE_EPS = {
    "air_temp_c": 0.2,      # <= 0.2°C range over window
    "rel_hum_pct": 1.0,     # <= 1% RH range
    "press_hpa": 0.3,       # <= 0.3 hPa range
    "wind_spd_ms": 0.2,     # <= 0.2 m/s range
    # wind_dir_deg: usually NOT good for flatline due to wrap-around; skip for now
}

SQL_FLATLINE = """
with windowed as (
  select
    f.station_id,
    f.metric_id,
    m.metric_code,
    f.value_num,
    f.observed_at
  from public.fact_observation f
  join public.dim_metric m
    on m.metric_id = f.metric_id
  where f.observed_at >= now() - (interval '1 minute' * %s)
),
agg as (
  select
    station_id,
    metric_id,
    metric_code,
    count(*) as n_points,
    min(observed_at) as window_start_at,
    max(observed_at) as window_end_at,
    min(value_num) as v_min,
    max(value_num) as v_max
  from windowed
  group by station_id, metric_id, metric_code
)
select
  'flatline'::text as anomaly_type,
  s.station_id,
  a.metric_id,
  'medium'::text as severity,
  jsonb_build_object(
    'metric_code', a.metric_code,
    'window_minutes', %s,
    'min_points', %s,
    'points', a.n_points,
    'window_start_at', a.window_start_at,
    'window_end_at', a.window_end_at,
    'min_value', a.v_min,
    'max_value', a.v_max,
    'range', (a.v_max - a.v_min),
    'epsilon', (cfg.cfg ->> a.metric_code)::numeric
  ) as details
from agg a
join public.dim_station s
  on s.station_id = a.station_id
cross join (select %s::jsonb as cfg) cfg
where s.is_current = true
  and s.is_smoketest = false
  and a.n_points >= %s
  and (cfg.cfg ? a.metric_code)
  and (a.v_max - a.v_min) <= (cfg.cfg ->> a.metric_code)::numeric;
"""

def detect(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            SQL_FLATLINE,
            (
                LOOKBACK_MINUTES,
                LOOKBACK_MINUTES,
                MIN_POINTS,
                Json(FLATLINE_EPS),
                MIN_POINTS,
            ),
        )
        return cur.fetchall()
