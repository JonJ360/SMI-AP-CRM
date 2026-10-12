-- AP only. Ingestion stays owner-only via existing authorized management channel.
-- No grants to anon/authenticated/service_role, no cross-app schema changes.
create table public.ap_snapshot_previous (like public.ap_snapshot including all);
create table public.ap_refresh_receipts (source_asof timestamptz primary key, checked_at timestamptz not null default now(), counts jsonb not null);
alter table public.ap_snapshot_previous enable row level security;
alter table public.ap_snapshot_previous force row level security;
alter table public.ap_refresh_receipts enable row level security;
alter table public.ap_refresh_receipts force row level security;
revoke all on public.ap_snapshot_previous,public.ap_refresh_receipts from public,anon,authenticated,service_role;
create function public.ap_publish_checked(p jsonb) returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare c text; n integer; info jsonb; stamp timestamptz; counts jsonb:='{}';
begin
 perform pg_advisory_xact_lock(71012026,1);
 if p->>'source' is distinct from 'GP SELECT-only snapshot' or jsonb_typeof(p->'companies') is distinct from 'object' or jsonb_typeof(p->'rows') is distinct from 'array' then raise exception 'Source shape'; end if;
 if (select array_agg(k order by k) from jsonb_object_keys(p->'companies') k) is distinct from array['SFAB','SMI'] then raise exception 'Company coverage'; end if;
 stamp:=(p->>'asof')::timestamptz;
 if stamp is null or stamp<now()-interval '4 minutes' or stamp>now()+interval '1 minute' then raise exception 'Source freshness'; end if;
 if exists(select 1 from public.ap_snapshot where (payload->>'asof')::timestamptz>stamp) then raise exception 'Stale generation'; end if;
 if exists(select 1 from jsonb_array_elements(p->'rows') r where r->>'company' is null or r->>'company' not in ('SMI','SFAB') or r->>'id' is null or r->>'id' not like (r->>'company')||':%') or (select count(*)<>count(distinct r->>'id') from jsonb_array_elements(p->'rows') r) then raise exception 'Row identity'; end if;
 foreach c in array array['SMI','SFAB'] loop
  info:=p->'companies'->c;
  select count(*) into n from jsonb_array_elements(p->'rows') r where r->>'company'=c;
  if n<1 or n>10000 or (info->>'count')::integer is distinct from n or (info->>'stable_reread')::boolean is distinct from true or (info->'vendor_reconciliation'->>'difference_cents')::bigint is distinct from 0 then raise exception 'Reconciliation'; end if;
  counts:=counts||jsonb_build_object(c,n);
 end loop;
 -- Lock both current rows in fixed order; ap_update uses these same locks.
 perform 1 from public.ap_snapshot order by company for update;
 if exists(select 1 from public.ap_refresh_receipts where source_asof=stamp) then
  if exists(select 1 from public.ap_snapshot s where s.payload <> (p||jsonb_build_object('rows',(select jsonb_agg(r) from jsonb_array_elements(p->'rows') r where r->>'company'=s.company),'companies',jsonb_build_object(s.company,p->'companies'->s.company)))) then raise exception 'Generation mismatch'; end if;
  return jsonb_build_object('status','already_published','source_asof',stamp,'counts',counts);
 end if;
 insert into public.ap_snapshot_previous select * from public.ap_snapshot on conflict(company) do update set payload=excluded.payload,updated_at=excluded.updated_at;
 foreach c in array array['SMI','SFAB'] loop
  insert into public.ap_snapshot(company,payload) values(c,p||jsonb_build_object('rows',(select jsonb_agg(r) from jsonb_array_elements(p->'rows') r where r->>'company'=c),'companies',jsonb_build_object(c,p->'companies'->c))) on conflict(company) do update set payload=excluded.payload,updated_at=now();
 end loop;
 insert into public.ap_refresh_receipts(source_asof,counts) values(stamp,counts);
 return jsonb_build_object('status','published','source_asof',stamp,'counts',counts);
end $$;
revoke all on function public.ap_publish_checked(jsonb) from public,anon,authenticated,service_role;
