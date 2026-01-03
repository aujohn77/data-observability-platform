 WITH open_incidents AS (
         SELECT (count(*))::integer AS open_incidents
           FROM ops_incident
          WHERE (ops_incident.status <> 'resolved'::text)
        ), freshness AS (
         SELECT (GREATEST((0)::numeric, floor((EXTRACT(epoch FROM (now() - max(f.observed_at))) / (60)::numeric))))::integer AS worst_freshness_minutes
           FROM fact_observation f
        ), dq_issues AS (
         SELECT (count(*))::integer AS bad_checks
           FROM ops_dq_check_run
          WHERE ((ops_dq_check_run.status = ANY (ARRAY['warn'::text, 'fail'::text])) AND (ops_dq_check_run.evaluated_at >= (now() - '24:00:00'::interval)))
        ), last_ingest AS (
         SELECT max(ops_job_run.started_at) AS last_ingest_at
           FROM ops_job_run
          WHERE ((ops_job_run.job_name = 'ingest_openmeteo_all_stations'::text) AND (ops_job_run.status = 'succeeded'::text))
        )
 SELECT
        CASE
            WHEN (oi.open_incidents > 0) THEN 'RED'::text
            WHEN ((fr.worst_freshness_minutes > 120) OR (dq.bad_checks > 0)) THEN 'AMBER'::text
            ELSE 'GREEN'::text
        END AS status,
    fr.worst_freshness_minutes,
    dq.bad_checks,
    oi.open_incidents,
    li.last_ingest_at AS last_ingest,
    now() AS evaluated_at
   FROM (((open_incidents oi
     CROSS JOIN freshness fr)
     CROSS JOIN dq_issues dq)
     CROSS JOIN last_ingest li);