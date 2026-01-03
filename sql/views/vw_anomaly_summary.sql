 SELECT t.anomaly_type,
    COALESCE(count(a.anomaly_id), (0)::bigint) AS anomalies_24h
   FROM (ops_anomaly_type t
     LEFT JOIN ops_anomaly a ON (((a.anomaly_type = t.anomaly_type) AND (a.detected_at >= (now() - '24:00:00'::interval)))))
  GROUP BY t.anomaly_type
  ORDER BY t.anomaly_type;