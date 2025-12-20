INSERT INTO dim_metric
(metric_code, unit_canonical, value_type, min_expected, max_expected, is_active)
VALUES
  ('temp_air_c','C','numeric',-10,55,true),
  ('rain_mm','mm','numeric',0,500,true),
  ('wind_speed_ms','m/s','numeric',0,60,true),
  ('wind_gust_ms','m/s','numeric',0,80,true),
  ('humidity_pct','%','numeric',0,100,true),
  ('pressure_hpa','hPa','numeric',850,1100,true)
ON CONFLICT (metric_code) DO NOTHING;



