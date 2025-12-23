# Security & Governance (RLS)

This project uses **Postgres Row-Level Security (RLS)** as the source of truth for authorization.
Access is enforced in the database (not only in application code) and continuously validated by CI.

## Roles (high level)

| Role | Intended user | Key idea |
|---|---|---|
| `anon` | public/unauthenticated | may see only safe metadata (no facts/raw) |
| `authenticated` + Analyst access | analyst users | read-only, region/station scoped |
| `authenticated` + Ops access | ops/admin users | operational access (raw + ops tables) |

> Note: “Analyst” and “Ops” are logical roles mapped through `authz_user_access` and helper functions (e.g., `is_role()`, `can_access_station()`).

## Protected tables (current)

- `raw_observations` — raw ingest zone (sensitive)
- `fact_observation` — modeled facts
- `dim_station` — station metadata
- `dim_metric` — metric dictionary
- Ops tables: `ops_job_run`, `ops_dq_check_run`, `ops_dq_check_definition`, `ops_anomaly`, `ops_anomaly_type`, `ops_incident`
- Authz: `authz_user_access`

## “Top 10” RLS checks (auditable, 1:1 with policies)

1. **Anon cannot read facts**  
   `anon` → `SELECT` from `fact_observation` → **0 rows** (or denied)

2. **Anon can read station metadata**  
   `anon` → `SELECT` from `dim_station` → **allowed** (safe subset)

3. **Analyst cannot read raw data**  
   analyst → `SELECT` from `raw_observations` → **0 rows / denied**

4. **Analyst sees only authorized stations**  
   analyst → `SELECT` from `dim_station` → **only stations allowed** by `can_access_station(...)`

5. **Analyst sees only authorized facts**  
   analyst → `SELECT` from `fact_observation` → **only facts for allowed stations**

6. **Analyst cannot write reference data**  
   analyst → `INSERT/UPDATE` on `dim_station` (and other reference tables) → **denied**

7. **Ops can read all facts**  
   ops → `SELECT` from `fact_observation` → **all rows**

8. **Ops can write operational tables**  
   ops → `INSERT` into `ops_job_run` / `ops_dq_check_run` → **allowed**

9. **Ops can read raw observations**  
   ops → `SELECT` from `raw_observations` → **allowed**

10. **Users can only see their own authz row**  
   any authenticated user → `SELECT` from `authz_user_access` → **only their own row**

## How CI proves it

A GitHub Actions workflow runs `psql` against Supabase and executes the test file:

- SQL tests: `db/tests/security_rls_smoke.sql`
- Workflow: `.github/workflows/security_rls_tests.yml`

Secrets are injected at runtime (no secrets/UUIDs in the repo):
- `SUPABASE_DB_URL`
- `ANA_UUID`, `BEN_UUID` (optional), `OPS_UUID`

## How to run manually (local)

```bash
psql "$SUPABASE_DB_URL" \
  -v ON_ERROR_STOP=1 \
  -v ana_uuid="$ANA_UUID" \
  -v ops_uuid="$OPS_UUID" \
  -f db/tests/security_rls_smoke.sql
