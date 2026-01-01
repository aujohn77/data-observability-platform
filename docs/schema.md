# Database Schema Overview

This schema is organized into three logical layers:
Raw, Warehouse, and Observability (Ops).

---

## Raw Layer

### raw_observations
Stores source data exactly as received.

Grain:
(source, station_external_id, observed_at, metric_code)

Key properties:
- Append-only
- Preserves source payload
- Used for audit and reprocessing

---

## Warehouse Layer

### fact_observation
Analytics-ready fact table for numeric metrics.

Grain:
(station_id, metric_id, observed_at)

Notes:
- One row per station, metric, and timestamp
- Joined to dimensions for context
- Late-arriving data flagged

### dim_station
Station reference data with historical tracking.

Notes:
- Surrogate key (station_id)
- Supports metadata changes over time

### dim_metric
Canonical metric dictionary.

Notes:
- Defines allowed metrics
- Enforces unit consistency

---

## Observability / Ops Layer

### ops_job_run
Tracks execution of ingestion and transform jobs.

### ops_dq_check_run
Stores results of data quality checks.

### ops_anomaly
Records detected data anomalies.

### ops_incident
Manages incident lifecycle.

---

## Relationships (Summary)

- raw_observations → source of truth
- fact_observation → analytics layer
- ops tables → operational metadata only

Foreign keys enforce referential integrity
between facts, dimensions, and ops tables.
