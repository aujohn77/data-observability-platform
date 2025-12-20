Schema v1 — Database Design

This document defines the initial database schema for the Data Observability Platform.
The schema is organized into three logical zones: Raw, Warehouse, and Observability/Ops.

The design prioritizes auditability, data quality, analytics readiness, and operational monitoring.

1. Zone Layout
1.1 Raw Zone (Append-Only)

Purpose:
Store ingested source data exactly as received, preserving full history and provenance.

Characteristics:

Append-only

Idempotent ingestion

No destructive updates

Tables:

raw_observations

raw_stations (optional; only if station metadata is ingested separately)

1.2 Warehouse Zone (Analytics-Ready)

Purpose:
Provide clean, normalized, query-optimized tables for analytics and reporting.

Characteristics:

Conformed dimensions

Stable fact grain

Supports slowly changing dimensions (SCD Type 2)

Tables:

dim_station

dim_metric

fact_observation

1.3 Observability / Ops Zone

Purpose:
Track pipeline execution, data quality results, anomalies, and incident workflows.

Characteristics:

Operational metadata only

Independent of business analytics tables

Enables monitoring and auditability

Tables:

ops_job_run

ops_dq_check_run

ops_dq_issue (or ops_dq_result)

ops_anomaly

ops_incident

Target size: 8–12 tables total (v1)

2. Table Definitions (v1)
2.1 raw_observations

Purpose:
Store raw observation events exactly as ingested from the source.

Grain:
(source, station_external_id, observed_at, metric_code)

Fields (minimum):

id (uuid or bigint, PK)

source

station_external_id

observed_at

metric_code

value_num

value_text

unit

quality_flag

source_payload

ingested_at

ingest_run_id

Constraints:

Unique: (source, station_external_id, observed_at, metric_code)

Check: value_num IS NOT NULL XOR value_text IS NOT NULL

Indexes:

(station_external_id, observed_at DESC)

(metric_code, observed_at DESC)

(ingested_at DESC)

2.2 dim_metric

Purpose:
Canonical dictionary of supported metrics.

Fields:

metric_id (PK)

metric_code (unique)

unit_canonical

value_type

min_expected (nullable)

max_expected (nullable)

is_active

2.3 dim_station (SCD Type 2)

Purpose:
Store station metadata with support for historical changes.

Fields:

station_id (PK, surrogate)

source

station_external_id

station_name

state

region

lat

lon

valid_from

valid_to

is_current

Constraints:

Exactly one current row per station:

Partial unique index on (source, station_external_id) where is_current = true

2.4 fact_observation

Purpose:
Analytics-ready fact table for numeric observations.

Grain:
One record per (station, metric, observed_at)

Fields:

station_id (FK → dim_station)

metric_id (FK → dim_metric)

observed_at

value_num

source

ingested_at

is_late

ingest_run_id (FK → ops_job_run)

Constraints:

Unique: (station_id, metric_id, observed_at)

Indexes:

(metric_id, observed_at DESC)

(station_id, observed_at DESC)

3. Observability / Ops Tables
3.1 ops_job_run

Purpose:
Track execution of ingestion, transformation, and quality jobs.

Fields:

run_id (PK, uuid)

job_name

status (started, succeeded, failed)

started_at

ended_at

watermark_from

watermark_to

rows_inserted

rows_updated

rows_deduped

error_message (nullable)

Indexes:

(job_name, started_at DESC)

(status, started_at DESC)

3.2 ops_dq_check_run

Purpose:
Store results of individual data quality checks.

Fields:

dq_run_id (PK)

run_id (FK → ops_job_run)

check_name

status (pass, warn, fail)

evaluated_at

metric_value

threshold

details (jsonb)

3.3 ops_anomaly

Purpose:
Record detected anomalies in data or ingestion behavior.

Typical fields:

anomaly_id (PK)

anomaly_type

detected_at

station_id (nullable)

metric_id (nullable)

severity

details (jsonb)

3.4 ops_incident

Purpose:
Manage incident lifecycle for operational follow-up.

Typical fields:

incident_id (PK)

status (open, acknowledged, resolved)

opened_at

resolved_at

anomaly_id (FK → ops_anomaly)

owner

notes

Relationship:

v1 supports a 1:1 relationship between incidents and anomalies

4. Entity Relationships (ERD — Textual)

raw_observations → source of truth for ingestion

dim_metric → referenced by fact_observation

dim_station → referenced by fact_observation

fact_observation → linked to ops_job_run

ops_job_run → parent of ops_dq_check_run

ops_anomaly → may generate ops_incident

5. Versioning

This document defines Schema v1.
All schema changes must be additive or versioned explicitly in future revisions.