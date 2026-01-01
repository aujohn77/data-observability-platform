# RLS policies (Supabase)

Source: `pg_policies` export from Supabase.

| schemaname | tablename | policyname | roles | cmd | permissive | using_expression | with_check_expression |
|---|---|---|---|---|---|---|---|
| public | authz_user_access | authz_self_read | {authenticated} | SELECT | PERMISSIVE | `(user_id = auth.uid())` | — |
| public | dim_metric | dim_metric_read | {public} | SELECT | PERMISSIVE | `is_role('ops') OR is_role('analyst')` | — |
| public | dim_metric | dim_metric_write_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | dim_station | dim_station_read | {public} | SELECT | PERMISSIVE | `can_access_station(station_id, region)` | — |
| public | dim_station | dim_station_write_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | fact_observation | fact_observation_read | {public} | SELECT | PERMISSIVE | <details><summary>show</summary><code>(EXISTS ( SELECT 1<br>FROM dim_station s<br>WHERE ((s.station_id = fact_observation.station_id) AND can_access_station(s.station_id, s.region))))</code></details> | — |
| public | fact_observation | fact_observation_write_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_anomaly | ops_anomaly_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_anomaly_detector_run | ops_anomaly_detector_run_ops_all | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_anomaly_type | anomaly_type_read | {public} | SELECT | PERMISSIVE | `is_role('ops') OR is_role('analyst')` | — |
| public | ops_anomaly_type | anomaly_type_write_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_dq_check_definition | ops_dq_check_definition_ops_only | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_dq_check_run | ops_dq_check_run_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_incident | ops_incident_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_incident_anomaly | ops_incident_anomaly_ops_all | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | ops_job_run | ops_job_run_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
| public | raw_observations | raw_observations_read_ops | {public} | SELECT | PERMISSIVE | `is_role('ops')` | — |
| public | raw_observations | raw_observations_write_ops | {public} | ALL | PERMISSIVE | `is_role('ops')` | `is_role('ops')` |
