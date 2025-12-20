Data Contracts & Semantics (v1)

This document defines the canonical data contracts and semantic rules for the Data Observability Platform.
It establishes the authoritative definitions for entities, fields, metrics, time semantics, and validation rules.

These contracts serve as the foundation for database design, ingestion logic, data quality checks, and analytics.

1. Core Entities
1.1 Observation Event

An observation event represents a single measured value for a specific metric at a station at a specific observation time.

Grain:
(station_id, observed_at, metric_code) → exactly one value

1.2 Station

A station represents a physical sensor location.

Station metadata (e.g. name, region, latitude/longitude) may change over time and is treated as slowly changing data.

1.3 Metric

A metric is a canonical definition of a measurement type (e.g. temperature, rainfall, wind speed).

Each metric includes:

A stable metric code

A canonical unit

A value type

An expected value range

2. Canonical Observation Schema (Raw Contract)
2.1 Observation Event Fields
Field	Type	Required	Description	Example
source	text	Yes	Data origin identifier	"BOM"
station_external_id	text	Yes	Source station identifier	"040913"
observed_at	timestamptz	Yes	Time the measurement was taken	2025-12-19T11:00:00+10:00
metric_code	text	Yes	Canonical metric identifier	"temp_air_c"
value_num	numeric	Conditional	Numeric measurement value	24.6
value_text	text	Optional	Non-numeric or categorical value	"CALM"
unit	text	Yes	Unit as delivered by source	"C"
quality_flag	text	Optional	Source-provided quality indicator	"OK"
source_payload	jsonb	Yes	Original source payload or subset	{...}
ingested_at	timestamptz	Yes	Time the record was stored	now()
ingest_run_id	uuid	Yes	Reference to ingestion job run	...

Value constraint:
Exactly one of value_num or value_text must be present.

2.2 Record Identity

A raw observation is uniquely identified by:

(source, station_external_id, observed_at, metric_code)


This identity is enforced via a deterministic key or unique constraint.

3. Canonical Metric Dictionary (v1)

The initial metric set is intentionally small and expandable.

metric_code	Description	Canonical Unit	Value Type	Expected Range (soft)
temp_air_c	Air temperature	C	numeric	-10 to 55
rain_mm	Rainfall over period	mm	numeric	0 to 500
wind_speed_ms	Wind speed	m/s	numeric	0 to 60
wind_gust_ms	Wind gust	m/s	numeric	0 to 80
humidity_pct	Relative humidity	%	numeric	0 to 100
pressure_hpa	Barometric pressure	hPa	numeric	850 to 1100

Metric rules:

Metric codes are snake_case

Metric codes are stable and never renamed

Unit normalization occurs in the warehouse layer

Raw data preserves the unit as delivered

4. Time Semantics
4.1 Event Time vs Platform Time

observed_at: the actual time the measurement occurred

ingested_at: the time the platform stored the record

Latency, freshness, and SLA calculations rely on both timestamps.

4.2 Allowed Lateness

Initial allowed lateness window: 24 hours

A record is classified as late if:

ingested_at > observed_at + 24 hours


The lateness window may be refined after observing real feed behavior.

5. Idempotency & Duplicate Handling

Two records represent the same observation if they share:

(source, station_external_id, observed_at, metric_code)


Handling of corrected or re-published source values:

Raw zone preserves received payloads according to identity rules

Modeled zone resolves to a single authoritative value for analytics

The identity definition is fixed at this stage.

6. Nullability & Validation Rules
6.1 Required Non-Null Fields

source

station_external_id

observed_at

metric_code

unit

ingested_at

ingest_run_id

source_payload

6.2 Value Rules

value_num IS NOT NULL XOR value_text IS NOT NULL

6.3 Metric Validation

metric_code must exist in the canonical metric dictionary

6.4 Range Validation

Values outside expected ranges generate data quality warnings

Out-of-range values do not block ingestion in v1

7. Versioning

This document defines Data Contracts v1.

All future changes must be backward-compatible or explicitly versioned.