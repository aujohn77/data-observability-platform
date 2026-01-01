flowchart TD
  A[External Data Sources<br/>(Public Sensors / APIs)]
  B[Ingestion Jobs<br/>(Scheduled / CI-trigger)<br/>• incremental<br/>• idempotent]
  C[RAW LAYER (Database)<br/>raw_observations<br/>• append-only<br/>• source payload stored]
  D[TRANSFORM / MODEL<br/>Jobs (CI / Workers)<br/>• normalize<br/>• deduplicate<br/>• enforce contracts]
  E[WAREHOUSE LAYER<br/>fact_observation<br/>dim_station<br/>dim_metric]
  F[OPS / OBSERVABILITY<br/>ops_job_run<br/>ops_dq_check_run<br/>ops_anomaly<br/>ops_incident]
  G[APPLICATION / DASHBOARD<br/>(Read-only views)<br/>• Status<br/>• Incidents<br/>• Stations]
  H[USERS<br/>• anon<br/>• analyst<br/>• ops<br/>(RLS enforced in DB)]

  A --> B --> C --> D --> E --> F --> G --> H
