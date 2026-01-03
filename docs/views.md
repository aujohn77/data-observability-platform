## Semantic Layer (Database Views used by Dashboards)

All dashboards query **read-only views** (semantic layer) instead of hitting raw tables.

### Control Tower
- `vw_platform_status` — overall platform status + last ingest window  
- `vw_pipeline_health` — job health + failures + last run  
- `vw_dq_summary` — data quality pass rates (by check / last 24h)  
- `vw_anomaly_summary` — active anomalies + severity breakdown  
- `vw_incident_kpis` — open/ack/resolved counts + SLA-style KPIs  

### Incidents
- `vw_incident_summary` — incident list with joins (anomaly/station/metric) and current status  

### Stations
- `public_station_freshness` — last observed timestamp + freshness minutes by station/metric  

### Source of truth (SQL)
- View definitions: `sql/views/` (one file per view)  
- Index: `docs/views.md` (what each view is for + which dashboard uses it)




*******************************


## Semantic Layer (Database Views used by Dashboards)

All dashboards query **read-only views** (semantic layer) instead of hitting raw tables.

### Control Tower
- `vw_platform_status` — overall platform status + last ingest window  
- `vw_pipeline_health` — job health + failures + last run  
- `vw_dq_summary` — data quality pass rates (by check / last 24h)  
- `vw_anomaly_summary` — active anomalies + severity breakdown  
- `vw_incident_kpis` — open/ack/resolved counts + SLA-style KPIs  

### Incidents
- `vw_incident_summary` — incident list with joins (anomaly/station/metric) and current status  

### Stations
- `public_station_freshness` — last observed timestamp + freshness minutes by station/metric  

### Source of truth (SQL)
- Folder: [`sql/views/`](../sql/views/)
- View definitions:
  - [`vw_platform_status.sql`](../sql/views/vw_platform_status.sql)
  - [`vw_pipeline_health.sql`](../sql/views/vw_pipeline_health.sql)
  - [`vw_dq_summary.sql`](../sql/views/vw_dq_summary.sql)
  - [`vw_anomaly_summary.sql`](../sql/views/vw_anomaly_summary.sql)
  - [`vw_incident_kpis.sql`](../sql/views/vw_incident_kpis.sql)
  - [`vw_incident_summary.sql`](../sql/views/vw_incident_summary.sql)
  - [`public_station_freshness.sql`](../sql/views/public_station_freshness.sql)
