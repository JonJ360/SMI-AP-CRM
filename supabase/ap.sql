-- AP-only objects. No inherited table access; exact immutable Auth UID on every RPC.
create table public.ap_snapshot(company text primary key check(company in ('SMI','SFAB')), payload jsonb not null, updated_at timestamptz not null default now());
create table public.ap_workflow(company text not null references public.ap_snapshot(company), id text not null, hold boolean not null default false, selected boolean not null default false, note text not null default '' check(length(note)<=2000), fingerprint text not null, primary key(company,id));
create table public.ap_audit(seq bigint generated always as identity primary key, at timestamptz not null default now(), actor uuid not null, company text not null, id text not null, before_json jsonb, after_json jsonb not null);
alter table public.ap_snapshot enable row level security;
alter table public.ap_snapshot force row level security;
alter table public.ap_workflow enable row level security;
alter table public.ap_workflow force row level security;
alter table public.ap_audit enable row level security;
alter table public.ap_audit force row level security;
revoke all on public.ap_snapshot,public.ap_workflow,public.ap_audit from public,anon,authenticated,service_role;
revoke all on sequence public.ap_audit_seq_seq from public,anon,authenticated,service_role;
create function public.ap_read(p_company text) returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
begin
 if auth.uid() is distinct from 'b605d98f-498e-4a94-94cf-e055ed2b5fcc'::uuid then raise exception 'Jon only' using errcode='42501'; end if;
 if p_company not in ('SMI','SFAB') or p_company is null then raise exception 'Company'; end if;
 return jsonb_build_object('snapshot',(select payload from public.ap_snapshot where company=p_company),'workflow',coalesce((select jsonb_agg(to_jsonb(w) || jsonb_build_object('selected',w.selected and w.fingerprint=md5(r::text) and not w.hold and not (r->>'gp_hold')::boolean and (r->>'cents')::bigint>0)) from public.ap_workflow w join public.ap_snapshot s on s.company=w.company cross join lateral jsonb_array_elements(s.payload->'rows') r where w.company=p_company and r->>'id'=w.id),'[]'::jsonb));
end $$;
create function public.ap_update(p_company text,p_id text,p_patch jsonb) returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare src jsonb; old public.ap_workflow; n public.ap_workflow; fp text;
begin
 if auth.uid() is distinct from 'b605d98f-498e-4a94-94cf-e055ed2b5fcc'::uuid then raise exception 'Jon only' using errcode='42501'; end if;
 if p_company not in ('SMI','SFAB') or p_company is null then raise exception 'Company'; end if;
 if p_patch is null or jsonb_typeof(p_patch)<>'object' or p_patch - array['hold','selected','note'] <> '{}'::jsonb then raise exception 'Invalid patch'; end if;
 if (p_patch ? 'hold' and jsonb_typeof(p_patch->'hold')<>'boolean') or (p_patch ? 'selected' and jsonb_typeof(p_patch->'selected')<>'boolean') or (p_patch ? 'note' and (jsonb_typeof(p_patch->'note')<>'string' or length(p_patch->>'note')>2000)) then raise exception 'Invalid patch type'; end if;
 -- Serialize workflow against snapshot replacement, including first insertion.
 perform 1 from public.ap_snapshot where company=p_company for update;
 select r into src from public.ap_snapshot s, lateral jsonb_array_elements(s.payload->'rows') r where s.company=p_company and r->>'id'=p_id;
 if src is null then raise exception 'Unknown document'; end if;
 fp:=md5(src::text);
 select * into old from public.ap_workflow where company=p_company and id=p_id;
 n.company:=p_company; n.id:=p_id; n.fingerprint:=fp;
 n.hold:=coalesce((p_patch->>'hold')::boolean,old.hold,false);
 n.note:=coalesce(p_patch->>'note',old.note,'');
 n.selected:=coalesce((p_patch->>'selected')::boolean,coalesce(old.selected,false) and old.fingerprint=fp,false);
 if coalesce((p_patch->>'selected')::boolean,false) and (n.hold or (src->>'gp_hold')::boolean or (src->>'cents')::bigint<=0) then raise exception 'Held or credit document'; end if;
 if n.hold or (src->>'gp_hold')::boolean or (src->>'cents')::bigint<=0 then n.selected:=false; end if;
 insert into public.ap_workflow values(n.*) on conflict(company,id) do update set hold=excluded.hold,selected=excluded.selected,note=excluded.note,fingerprint=excluded.fingerprint;
 insert into public.ap_audit(actor,company,id,before_json,after_json) values(auth.uid(),p_company,p_id,to_jsonb(old),to_jsonb(n));
 return jsonb_build_object('saved',true);
end $$;
revoke all on function public.ap_read(text),public.ap_update(text,text,jsonb) from public,anon,authenticated,service_role;
grant execute on function public.ap_read(text),public.ap_update(text,text,jsonb) to authenticated;
