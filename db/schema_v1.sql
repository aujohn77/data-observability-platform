/* ============================================================
   Data Observability Platform — Schema v1
   Postgres / Supabase
   ============================================================ */

CREATE EXTENSION IF NOT EXISTS pgcrypto;

BEGIN;

/* ===================== OPS / OBS ===================== */

CREATE TABLE IF NOT EXISTS ops_job_run (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name text NOT NULL,
  status text NOT NULL CHECK (status IN ('started','succeeded','failed')),
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  watermark_from timestamptz,
  watermark_to timestamptz,
  rows_inserted integer NOT NULL DEFAULT 0,
  rows_updated integer NOT NULL DEFAULT 0,
  rows_deduped integer NOT NULL DEFAULT 0,
  error_message text
);

CREATE INDEX IF NOT EXISTS idx_ops_job_run_job_started
  ON ops_job_run (job_name, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_ops_job_run_status_started
  ON ops_job_run (status, started_at DESC);


CREATE TABLE IF NOT EXISTS ops_dq_check_run (
  dq_run_id bigserial PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES ops_job_run(run_id) ON DELETE CASCADE,
  check_name text NOT NULL,
  status text NOT NULL CHECK (status IN ('pass','warn','fail')),
  evaluated_at timestamptz NOT NULL DEFAULT now(),
  metric_value numeric,
  threshold numeric,
  details jsonb NOT NULL DEFAULT '{}'::jsonb
);


CREATE TABLE IF NOT EXISTS ops_anomaly (
  anomaly_id bigserial PRIMARY KEY,
  anomaly_type text NOT NULL,
  detected_at timestamptz NOT NULL DEFAULT now(),
  station_id bigint,
  metric_id bigint,
  severity text NOT NULL CHECK (severity IN ('low','medium','high','critical')),
  details jsonb NOT NULL DEFAULT '{}'::jsonb
);


CREATE TABLE IF NOT EXISTS ops_incident (
  incident_id bigserial PRIMARY KEY,
  status text NOT NULL CHECK (status IN ('open','acknowledged','resolved')),
  opened_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  anomaly_id bigint UNIQUE REFERENCES ops_anomaly(anomaly_id),
  owner text,
  notes text
);


/* ===================== WAREHOUSE ===================== */

CREATE TABLE IF NOT EXISTS dim_metric (
  metric_id bigserial PRIMARY KEY,
  metric_code text NOT NULL UNIQUE,
  unit_canonical text NOT NULL,
  value_type text NOT NULL CHECK (value_type IN ('numeric','text')),
  min_expected numeric,
  max_expected numeric,
  is_active boolean NOT NULL DEFAULT true
);


CREATE TABLE IF NOT EXISTS dim_station (
  station_id bigserial PRIMARY KEY,
  source text NOT NULL,
  station_external_id text NOT NULL,
  station_name text,
  state text,
  region text,
  lat numeric,
  lon numeric,
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_to timestamptz,
  is_current boolean NOT NULL DEFAULT true
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_station_current
  ON dim_station (source, station_external_id)
  WHERE is_current = true;


CREATE TABLE IF NOT EXISTS fact_observation (
  station_id bigint NOT NULL REFERENCES dim_station(station_id),
  metric_id bigint NOT NULL REFERENCES dim_metric(metric_id),
  observed_at timestamptz NOT NULL,
  value_num numeric NOT NULL,
  source text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  is_late boolean NOT NULL DEFAULT false,
  ingest_run_id uuid NOT NULL REFERENCES ops_job_run(run_id),
  PRIMARY KEY (station_id, metric_id, observed_at)
);


/* ===================== RAW ===================== */

CREATE TABLE IF NOT EXISTS raw_observations (
  id bigserial PRIMARY KEY,
  source text NOT NULL,
  station_external_id text NOT NULL,
  observed_at timestamptz NOT NULL,
  metric_code text NOT NULL,
  value_num numeric,
  value_text text,
  unit text NOT NULL,
  quality_flag text,
  source_payload jsonb NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  ingest_run_id uuid NOT NULL REFERENCES ops_job_run(run_id),

  CONSTRAINT ux_raw_identity
    UNIQUE (source, station_external_id, observed_at, metric_code),

  CONSTRAINT ck_value_xor
    CHECK (
      (value_num IS NOT NULL AND value_text IS NULL)
      OR
      (value_num IS NULL AND value_text IS NOT NULL)
    )
);

COMMIT;
