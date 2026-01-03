 SELECT count(*) FILTER (WHERE (status = 'open'::text)) AS open_count,
    count(*) FILTER (WHERE (status = 'acknowledged'::text)) AS acknowledged_count,
    count(*) FILTER (WHERE (status = 'resolved'::text)) AS resolved_count_total,
    count(*) FILTER (WHERE ((status = 'resolved'::text) AND (opened_at >= (now() - '24:00:00'::interval)))) AS resolved_count_24h,
    (floor((EXTRACT(epoch FROM (now() - min(opened_at))) / (60)::numeric)))::integer AS oldest_active_minutes
   FROM ops_incident;