INSERT INTO ops_anomaly_type
(anomaly_type, description, default_severity, is_enabled)
VALUES
  ('spike', 'Sudden upward jump in a metric relative to recent baseline.', 'medium', true),
  ('drop', 'Sudden downward drop in a metric relative to recent baseline.', 'medium', true),
  ('silent_station', 'Station stopped reporting any observations for one or more metrics.', 'high', true),
  ('stale_data', 'Observations continue but observed_at does not advance (stuck timestamps).', 'high', true),
  ('flatline', 'Metric values stop changing over an extended window (possible sensor failure).', 'medium', true)
ON CONFLICT (anomaly_type) DO UPDATE
SET description = EXCLUDED.description,
    default_severity = EXCLUDED.default_severity,
    is_enabled = EXCLUDED.is_enabled;
