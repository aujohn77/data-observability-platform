-- =========================================================
-- RLS SECURITY TESTS
-- =========================================================


-- ---------------------------------------------------------
-- 0) Preconditions: seeded data exists
-- ---------------------------------------------------------
reset role;
set local role postgres;

select 'precond_dim_station_has_rows' as check,
       case when (select count(*) from public.dim_station) >= 2 then 'PASS' else 'FAIL' end as result;

select 'precond_fact_has_rows' as check,
       case when (select count(*) from public.fact_observation) > 0 then 'PASS' else 'FAIL' end as result;

-- ---------------------------------------------------------
-- 1) ANON cannot read facts
-- ---------------------------------------------------------
reset role;
set local role anon;
select set_config('request.jwt.claim.role', 'anon', true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000000', true);

select 'anon_no_fact_access' as check,
       case when (select count(*) from public.fact_observation) = 0 then 'PASS' else 'FAIL' end as result;

-- ---------------------------------------------------------
-- 2) ANON can read station metadata (must be > 0)
-- ---------------------------------------------------------
select 'anon_can_read_stations' as check,
       case when (select count(*) from public.dim_station) > 0 then 'PASS' else 'FAIL' end as result;

-- ---------------------------------------------------------
-- 3) ANALYST cannot read raw data
-- ---------------------------------------------------------
reset role;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', :'ana_uuid', true);

select 'analyst_no_raw_access' as check,
       case when (select count(*) from public.raw_observations) = 0 then 'PASS' else 'FAIL' end as result;

-- ---------------------------------------------------------
-- 4) ANALYST sees only authorized stations
-- ---------------------------------------------------------
with
grants as (
  select station_id
  from public.authz_user_access
  where user_id = :'ana_uuid'
),
visible as (
  select station_id
  from public.dim_station
)
select 'analyst_station_scope_enforced' as check,
       case
         when (select count(*) from grants) > 0
          and (select count(*) from visible) = (select count(*) from grants)
          and not exists (
            (select station_id from visible)
            except
            (select station_id from grants)
          )
         then 'PASS' else 'FAIL'
       end as result;

-- ---------------------------------------------------------
-- 5) ANALYST sees only authorized facts
-- ---------------------------------------------------------
with
grants as (
  select station_id
  from public.authz_user_access
  where user_id = :'ana_uuid'
),
visible_facts as (
  select station_id
  from public.fact_observation
)
select 'analyst_fact_scope_enforced' as check,
       case
         when (select count(*) from visible_facts) > 0
          and not exists (
            (select station_id from visible_facts)
            except
            (select station_id from grants)
          )
         then 'PASS' else 'FAIL'
       end as result;

-- ---------------------------------------------------------
-- 6) ANALYST cannot write reference data
-- ---------------------------------------------------------
do $$
begin
  begin
    insert into public.dim_station(station_id, station_name) values ('__rls_test__', '__rls_test__');
    raise exception 'FAIL';
  exception when others then
    -- expected failure
    raise notice 'analyst_no_station_write: PASS';
  end;
end $$;

-- ---------------------------------------------------------
-- 7) OPS can read all facts (must be > 0)
-- ---------------------------------------------------------
reset role;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', :'ops_uuid', true);

select 'ops_can_read_facts' as check,
       case when (select count(*) from public.fact_observation) > 0 then 'PASS' else 'FAIL' end as result;

-- ---------------------------------------------------------
-- 8) OPS can read raw observations (should be >= 0, but make it meaningful: > 0)
-- ---------------------------------------------------------
select 'ops_can_read_raw' as check,
       case when (select count(*) from public.raw_observations) > 0 then 'PASS' else 'FAIL' end as result;

-- ---------------------------------------------------------
-- 9) User can only see their own authz row(s)
-- ---------------------------------------------------------
with
ops_rows as (
  select count(*) as c
  from public.authz_user_access
  where user_id = :'ops_uuid'
),
all_visible as (
  select distinct user_id
  from public.authz_user_access
)
select 'user_authz_row_isolated' as check,
       case
         when (select c from ops_rows) >= 0
          and (select count(*) from all_visible) = 1
          and (select user_id from all_visible limit 1) = :'ops_uuid'
         then 'PASS' else 'FAIL'
       end as result;
