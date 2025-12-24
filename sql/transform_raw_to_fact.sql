-- Transforms raw_observations.payload (jsonb) into fact_observation rows.
-- Adjust the JSON paths to match your payload structure.

insert into public.fact_observation (station_id, observed_at, metric_id, value, unit, created_at)
select
  r.station_id,
  r.observed_at,
  m.metric_id,
  (x.value)::numeric as value,
  x.unit,
  now() as created_at
from public.raw_observations r
cross join lateral (
  -- Example: payload contains an array of measurements
  -- payload: { "measurements": [ {"metric":"temp","value":23.1,"unit":"C"}, ... ] }
  select
    (j->>'metric') as metric_code,
    (j->>'value')  as value,
    (j->>'unit')   as unit
  from jsonb_array_elements(r.source_payload->'measurements') as j
) x
join public.dim_metric m
  on m.metric_code = x.metric_code
-- Only transform rows not already in fact (idempotent)
on conflict (station_id, metric_id, observed_at) do update
set value = excluded.value,
    unit  = excluded.unit;
