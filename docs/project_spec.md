Data Observability Platform — Project Specification (v1)

This document defines the scope, purpose, and success criteria for the Data Observability Platform.
It establishes the production narrative that guides all architectural and implementation decisions.

1. Project Overview

The Data Observability Platform is a production-style system designed to ingest public sensor time-series data, model it into analytics-ready tables, and continuously monitor data reliability, quality, and operational health.

The platform demonstrates how modern data systems are designed, governed, secured, and operated, rather than focusing solely on data collection.

2. Data Domain

Domain:
Australian Bureau of Meteorology (BOM) public weather station data
(or an equivalent public sensor feed with time-series characteristics)

Rationale:

Real-world, late-arriving, and imperfect data

Multiple stations creating natural partitioning and multi-tenant patterns

Clear expectations for freshness, completeness, and accuracy

Familiar domain with non-trivial operational challenges

Data characteristics:

Time-stamped observations (hourly or sub-hourly)

Multiple metrics per station (e.g. temperature, rainfall, wind)

Station metadata that may change over time

3. Users and Roles

The platform explicitly models role-based access and governance.

Role	Description
Public Viewer	Access to high-level aggregated metrics and platform health
Analyst	Query access to curated facts and dimensions for approved regions
Ops / Admin	Full access to raw data, job runs, incidents, and data quality results
Tenant (optional)	Restricted access to assigned stations or regions

Security is enforced at the database level, independent of application-layer permissions.

4. Problems Addressed

The platform is designed to answer core operational data questions:

Is the latest data fresh?

Are ingestion jobs succeeding reliably?

Is data arriving late or missing?

Are there anomalies or silent failures?

Are access restrictions correctly enforced across users?

5. Core Reliability KPIs

The platform defines the following first-class reliability metrics:

Data Freshness
Time since the most recent successful observation per station and metric

Ingestion Success Rate
Percentage of scheduled ingestion jobs that complete successfully

Late Data Rate
Percentage of observations arriving outside the allowed lateness window

Anomaly Rate
Frequency of detected spikes, drops, or silent stations

Data Quality Pass Rate
Percentage of records passing completeness, validity, and consistency checks

These KPIs are stored and computed as data assets, not only as dashboard calculations.

6. Technical Capabilities Demonstrated

This project demonstrates proficiency in:

Data modeling (raw → facts → dimensions)

Incremental and idempotent ingestion

Data quality engineering

Observability and incident tracking

Database-native security (roles, RLS, least privilege)

Production automation (scheduled jobs, backfills)

Clean system design and technical documentation

The platform is intentionally designed as a mini data platform, not a toy ETL pipeline.

7. Non-Goals

To maintain focus and realistic scope:

No real-time streaming (batch processing is intentional)

No machine learning forecasting

No over-engineered user interface

8. Expected Final State

At completion, the repository contains:

A documented database schema (ERD)

Automated ingestion, transformation, and monitoring workflows

Enforced database security policies

Operational and reliability dashboards

Clear documentation suitable for technical review and recruitment

9. Versioning

This document defines Project Specification v1.
All future scope changes must be documented explicitly.