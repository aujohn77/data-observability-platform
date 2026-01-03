 SELECT
        CASE
            WHEN (resolved_at IS NOT NULL) THEN 'resolved'::text
            WHEN (acknowledged_at IS NOT NULL) THEN 'acknowledged'::text
            ELSE 'open'::text
        END AS status,
    COALESCE(opened_at, created_at) AS opened_at,
    COALESCE(severity, 'unknown'::text) AS severity,
    ((initcap(replace(anomaly_type, '_'::text, ' '::text)) || ' incident #'::text) || (incident_id)::text) AS title,
    station_id,
    metric_id
   FROM ops_incident i;