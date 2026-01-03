 SELECT check_name,
        CASE
            WHEN (status = 'pass'::text) THEN 'succeeded'::text
            ELSE 'failed'::text
        END AS status,
    evaluated_at AS last_run_at
   FROM ( SELECT d.check_name,
            d.status,
            d.evaluated_at,
            row_number() OVER (PARTITION BY d.check_name ORDER BY d.evaluated_at DESC) AS rn
           FROM ops_dq_check_run d) x
  WHERE (rn = 1)
  ORDER BY evaluated_at DESC NULLS LAST, check_name;