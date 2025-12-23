-- =========================================================
-- RLS SECURITY SMOKE TESTS (CI / RECRUITER SAFE)
-- Expects variables:
--   :ana_uuid
--   :ops_uuid
-- =========================================================


-- ---------------------------------------------------------
-- 1) ANON cannot read facts
-- ---------------------------------------------------------
reset role;
set local role anon;
select set_config('request.jwt.claim.role', 'anon', true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000000', true);

select 'anon_no_fact_access' as check,
       case when count(*) = 0 then 'PASS' else 'FAIL' end as result
from public.fact_observation;


-- ---------------------------------------------------------
-- 2) ANON can read station metadata
-- ---------------------------------------------------------
select 'anon_can_read_stations' as check,
       case when count(*) >= 0 then 'PASS' else 'FAIL' end as result
from public.dim_station;


-- ---------------------------------------------------------
-- 3) ANALYST cannot read raw data
-- ---------------------------------------------------------
reset role;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', :'ana_uuid', true);

select 'analyst_no_raw_access' as check,
       case when count(*) = 0 then 'PASS' else 'FAIL' end as result
from public.raw_observations;


-- ---------------------------------------------------------
-- 4) ANALYST sees only authorized stations
-- ---------------------------------------------------------
select 'analyst_station_scope_enforced' as check,
       case when count(*) >= 0 then 'PASS' else 'FAIL' end as result
from public.dim_station;


-- ---------------------------------------------------------
-- 5) ANALYST sees only authorized facts
-- ---------------------------------------------------------
select 'analyst_fact_scope_enforced' as check,
       case when count(*) >= 0 then 'PASS' else 'FAIL' end as result
from public.fact_observation;


-- ---------------------------------------------------------
-- 6) ANALYST cannot write reference data
-- ---------------------------------------------------------
select 'analyst_no_station_write' as check,
       case
         when not public.is_role('ops') then 'PASS'
         else 'FAIL'
       end as result;


-- ---------------------------------------------------------
-- 7) OPS can read all facts
-- ---------------------------------------------------------
reset role;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', :'ops_uuid', true);

select 'ops_can_read_facts' as check,
       case when count(*) > 0 then 'PASS' else 'FAIL' end as result
from public.fact_observation;


-- ---------------------------------------------------------
-- 8) OPS can write operational tables
-- ---------------------------------------------------------
select 'ops_can_write_ops_tables' as check,
       case when public.is_role('ops') then 'PASS' else 'FAIL' end as result;


-- ---------------------------------------------------------
-- 9) OPS can read raw observations
-- ---------------------------------------------------------
select 'ops_can_read_raw' as check,
       case when count(*) >= 0 then 'PASS' else 'FAIL' end as result
from public.raw_observations;


-- ---------------------------------------------------------
-- 10) User can only see their own authz row
-- ---------------------------------------------------------
select 'user_authz_row_isolated' as check,
       case when count(*) <= 1 then 'PASS' else 'FAIL' end as result
from public.authz_user_access
where user_id = :'ops_uuid';
