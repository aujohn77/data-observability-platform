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
