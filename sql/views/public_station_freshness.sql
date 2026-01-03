 SELECT s.station_id,
    s.station_name,
    max(f.observed_at) AS last_observed_at,
    (now() - max(f.observed_at)) AS staleness,
        CASE
            WHEN (max(f.observed_at) IS NULL) THEN 'MISSING'::text
            WHEN ((now() - max(f.observed_at)) > '02:00:00'::interval) THEN 'STALE'::text
            ELSE 'FRESH'::text
        END AS freshness,
    max(f.observed_at) AS last_seen
   FROM (dim_station s
     LEFT JOIN fact_observation f ON ((f.station_id = s.station_id)))
  WHERE ((s.is_current = true) AND (s.is_smoketest = false))
  GROUP BY s.station_id, s.station_name;