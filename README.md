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
