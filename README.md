
[![security-rls-tests](https://github.com/aujohn77/data-observability-platform/actions/workflows/security_rls_tests.yml/badge.svg)](https://github.com/aujohn77/data-observability-platform/actions/workflows/security_rls_tests.yml)


# Data Observability Platform

Production-style platform for ingesting time-series data, modeling it into analytics-ready tables, and monitoring reliability via data quality checks, operational metrics, and security controls.

## What it does (planned)
- Ingest: scheduled jobs pull data from external sources (APIs / feeds)
- Model: raw → clean facts/dimensions (analytics-ready)
- Observe: freshness, late data, anomaly rate, DQ pass rate, job success
- Secure: RBAC, least-privilege DB roles, secrets management, audit logging

## Repo structure (initial)
- `apps/ingest` — ingestion jobs + idempotent loads
- `apps/warehouse` — transformations + dimensional modeling
- `apps/quality` — data quality checks (freshness, nulls, duplicates, schema drift)
- `apps/observability` — metrics, incidents, job run tracking
- `apps/dashboards` — dashboards/UI endpoints
- `apps/authz` — roles/permissions/security policies

## Automation (planned)
- Daily scheduled workflow for ingestion + quality + metrics
- Optional monthly backfill workflow

## Project Documentation
- Project spec: [docs/project_spec.md](docs/project_spec.md)
- Data contracts: [docs/data_contracts.md](docs/data_contracts.md)
- Current stage: Stage 2 — Data contracts & semantics





## Database bootstrap (Supabase / Postgres)

Schema and reference data are managed via SQL scripts in `db/`.

Run in Supabase SQL Editor (in this order):

1. `db/schema_v1.sql` — core schema (raw + warehouse + ops tables)
2. `db/seed_metrics.sql` — seeds canonical metric dictionary (`dim_metric`)
3. `db/schema_v1_add_reference_tables.sql` — adds reference tables for governance
4. `db/seed_dq_check_definitions.sql` — seeds DQ checks (`ops_dq_check_definition`)
5. `db/seed_anomaly_types.sql` — seeds anomaly taxonomy (`ops_anomaly_type`)

### Seeded reference tables (truth)
- `dim_metric`: canonical metrics (codes, units, expected ranges)
- `ops_dq_check_definition`: data quality checks, default thresholds, severity
- `ops_anomaly_type`: anomaly taxonomy and default severity
