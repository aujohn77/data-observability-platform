INSERT INTO ops_dq_check_definition
(check_name, description, category, severity, default_threshold, is_enabled)
VALUES
  (
    'freshness_sla_minutes',
    'Maximum allowed minutes since last observation per station/metric. Exceeding threshold triggers warning/fail depending on severity policy.',
    'freshness', 'high', 120, true
  ),
  (
    'late_data_rate_pct',
    'Percentage of observations where ingested_at > observed_at + allowed_lateness. Threshold is percentage (0–100).',
    'consistency', 'medium', 5, true
  ),
  (
    'dup_rate_pct',
    'Percentage of duplicate raw observations by identity key (source, station_external_id, observed_at, metric_code). Threshold is percentage (0–100).',
    'consistency', 'medium', 1, true
  ),
  (
    'null_rate_pct',
    'Percentage of records violating required non-null fields in the contract. Threshold is percentage (0–100).',
    'completeness', 'high', 0, true
  ),
  (
    'range_temp_air_c',
    'Soft range validation for temp_air_c using dim_metric min_expected/max_expected. Counts out-of-range values. Threshold is percentage (0–100) of out-of-range records.',
    'validity', 'medium', 1, true
  ),
  (
    'metric_code_known_pct',
    'Percentage of observations whose metric_code exists in the canonical metric dictionary. Threshold is percentage (0–100) of unknown codes allowed.',
    'validity', 'critical', 0, true
  )
ON CONFLICT (check_name) DO UPDATE
SET description = EXCLUDED.description,
    category = EXCLUDED.category,
    severity = EXCLUDED.severity,
    default_threshold = EXCLUDED.default_threshold,
    is_enabled = EXCLUDED.is_enabled;
