BEGIN;

/* 1) start job */
INSERT INTO ops_job_run (job_name, status)
VALUES ('smoke_test_ingest','started')
RETURNING run_id;

/* Replace <RUN_ID> with returned value */

-- Example station
INSERT INTO dim_station
(source, station_external_id, station_name, state, region)
VALUES
('BOM','TEST001','Test Station','QLD','Gold Coast');

/* Raw observations */
INSERT INTO raw_observations
(source, station_external_id, observed_at, metric_code, value_num, unit, source_payload, ingest_run_id)
VALUES
('BOM','TEST001',now() - interval '1 hour','temp_air_c',25.2,'C','{}','<RUN_ID>'),
('BOM','TEST001',now() - interval '1 hour','humidity_pct',60,'%','{}','<RUN_ID>');

/* Finish job */
UPDATE ops_job_run
SET status='succeeded',
    ended_at=now(),
    rows_inserted=2
WHERE run_id='<RUN_ID>';

COMMIT;
