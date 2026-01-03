 SELECT job_name,
    started_at AS last_run_at,
    status AS last_status
   FROM ( SELECT ops_job_run.job_name,
            ops_job_run.status,
            ops_job_run.started_at,
            row_number() OVER (PARTITION BY ops_job_run.job_name ORDER BY ops_job_run.started_at DESC) AS rn
           FROM ops_job_run) t
  WHERE (rn = 1)
  ORDER BY started_at DESC;