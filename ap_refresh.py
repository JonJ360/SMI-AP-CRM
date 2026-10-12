"""Deterministic AP-only scheduled refresh. No LLM, arbitrary SQL or payment path.
Uses existing profile-bound renewable management OAuth; no new public RPC grants.
"""
import asyncio, contextlib, gzip, hashlib, io, json, os, shutil, sqlite3, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import gp_extract
ROOT=Path(__file__).resolve().parent
PRIVATE=gp_extract.PRIVATE
PROJECT='inhwadbibwkakacdvoxu'
PUBLISH_SQL='select public.ap_publish_checked({payload}::jsonb) as receipt'
def now(): return datetime.now(timezone.utc).isoformat()
def validate(s):
 if set(s.get('companies',{}))!={'SMI','SFAB'}: raise ValueError('Company coverage')
 if not s.get('rows') or s.get('source')!='GP SELECT-only snapshot': raise ValueError('Source coverage')
 if (datetime.now(timezone.utc)-datetime.fromisoformat(s['asof'])).total_seconds()>240: raise ValueError('Stale extraction')
 for c,v in s['companies'].items():
  rows=[r for r in s['rows'] if r['company']==c]
  if not rows or len(rows)!=v['count'] or not v['stable_reread'] or v['vendor_reconciliation']['difference_cents']!=0: raise ValueError('Reconciliation')
 if len({r['id'] for r in s['rows']})!=len(s['rows']): raise ValueError('Duplicate documents')
 if any(r['company'] not in ('SMI','SFAB') for r in s['rows']): raise ValueError('Company row')
def literal(v):
 return "'"+json.dumps(v,ensure_ascii=True,separators=(',',':')).replace("'","''")+"'"
class Backend:
 def __init__(self):
  h=Path.home()/'AppData/Local/hermes'
  if os.environ.get('HERMES_HOME') and Path(os.environ['HERMES_HOME']).resolve()!=h.resolve(): raise RuntimeError('Profile mismatch')
  sys.path.insert(0,str(h/'hermes-agent'))
  sys.path.insert(0,str(ROOT.parent/'SMI-AR-CRM/scripts'))
  from arcrm_ledger_auth import ensure_management_token
  from tools.mcp_oauth import build_oauth_auth
  import mcp.client.auth.oauth2 as sdk
  http=getattr(sdk,'httpx2',None) or getattr(sdk,'httpx')
  async def token():
   provider=build_oauth_auth('supabase','https://mcp.supabase.com/mcp')
   async with http.AsyncClient(timeout=60,follow_redirects=False) as client:
    await ensure_management_token(provider,client)
   return provider.context.current_tokens.access_token
  self._token=asyncio.run(token())
 def query(self,q):
  import requests
  r=requests.post(f'https://api.supabase.com/v1/projects/{PROJECT}/database/query',headers={'Authorization':'Bearer '+self._token},json={'query':q},timeout=70)
  if r.status_code not in (200,201): raise RuntimeError('AP backend HTTP '+str(r.status_code))
  result=r.json()
  if not isinstance(result,list): raise RuntimeError('AP backend response')
  return result
EXPORT_SQL="""select jsonb_build_object('ap_snapshot',(select coalesce(jsonb_agg(to_jsonb(t)),'[]') from public.ap_snapshot t),'ap_workflow',(select coalesce(jsonb_agg(to_jsonb(t)),'[]') from public.ap_workflow t),'ap_audit',(select coalesce(jsonb_agg(to_jsonb(t)),'[]') from public.ap_audit t)) as backup"""
def backup(backend,run):
 data=backend.query(EXPORT_SQL)[0]['backup']
 b=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
 with gzip.open(run/'cloud-backup.json.gz','wb') as f:f.write(b)
 # Restore to a separate private SQLite target, never to any production endpoint.
 with sqlite3.connect(run/'isolated-restore.sqlite3') as db:
  for table,rows in data.items():
   if table not in ('ap_snapshot','ap_workflow','ap_audit'): raise ValueError('Backup scope')
   db.execute('create table '+table+' (ordinal integer primary key, payload text not null)')
   db.executemany('insert into '+table+' values (?,?)',[(i,json.dumps(row,sort_keys=True,separators=(',',':'))) for i,row in enumerate(rows)])
  restored={t:[json.loads(r[0]) for r in db.execute('select payload from '+t+' order by ordinal')] for t in data}
  if restored!=data or db.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Restore mismatch')
 if (PRIVATE/'workflow.sqlite3').exists():
  with sqlite3.connect(PRIVATE/'workflow.sqlite3') as src,sqlite3.connect(run/'local-workflow.sqlite3') as dst:
   src.backup(dst)
   if dst.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Local backup integrity')
 if (PRIVATE/'snapshot.json').exists():shutil.copy2(PRIVATE/'snapshot.json',run/'previous-local-snapshot.json')
 return {'sha256':hashlib.sha256(b).hexdigest(),'counts':{t:len(v) for t,v in data.items()},'isolated_restore':'exact JSON roundtrip + SQLite integrity; not PostgreSQL schema restore'}
def run():
 import msvcrt
 PRIVATE.mkdir(parents=True,exist_ok=True)
 lock=open(PRIVATE/'refresh.lock','a+b')
 lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
 try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 except OSError:lock.close();return 0
 started=time.monotonic();run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
 folder=PRIVATE/'runs'/run_id;folder.mkdir(parents=True)
 receipt={'run_id':run_id,'started_at':now(),'status':'started'}
 def save():
  p=folder/'receipt.json';p.write_text(json.dumps(receipt,indent=2))
  temp=PRIVATE/'latest-receipt.tmp';temp.write_text(json.dumps(receipt,indent=2));temp.replace(PRIVATE/'latest-receipt.json')
 save()
 try:
  backend=Backend()
  receipt['backup']=backup(backend,folder);save()
  gp_extract.PRIVATE=folder
  with contextlib.redirect_stdout(io.StringIO()):gp_extract.main()
  s=json.loads((folder/'snapshot.json').read_text());validate(s)
  receipt['source_asof']=s['asof'];receipt['counts']={c:v['count'] for c,v in s['companies'].items()}
  receipt['extraction_seconds']=round(time.monotonic()-started,3);save()
  result=backend.query(PUBLISH_SQL.format(payload=literal(s)))[0]['receipt']
  expected={c:{**s,'rows':[r for r in s['rows'] if r['company']==c],'companies':{c:s['companies'][c]}} for c in ('SMI','SFAB')}
  equality='case company '+''.join("when '"+c+"' then payload="+literal(p)+'::jsonb ' for c,p in expected.items())+'end'
  check=backend.query("select company,payload->>'asof' as source_asof,jsonb_array_length(payload->'rows') as documents,payload->>'query_sha256' as query_sha256,updated_at,"+equality+" as exact_payload_matches from public.ap_snapshot order by company")
  if {r['company'] for r in check}!={'SMI','SFAB'} or any(not r['exact_payload_matches'] or r['source_asof']!=s['asof'] or r['documents']!=s['companies'][r['company']]['count'] or r['query_sha256']!=s['query_sha256'] for r in check):raise ValueError('Readback mismatch')
  temp=PRIVATE/'snapshot.tmp';shutil.copyfile(folder/'snapshot.json',temp);temp.replace(PRIVATE/'snapshot.json')
  receipt.update(status='verified',publish=result,readback=check)
  code=0
 except Exception as e:
  receipt.update(status='blocked',error_type=type(e).__name__,note='No raw exception/credentials logged. Prior snapshots retained; check AP-only source/backend access.')
  code=1
 finally:
  receipt.update(completed_at=now(),elapsed_seconds=round(time.monotonic()-started,3));save()
  lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()
 print(json.dumps(receipt));return code
if __name__=='__main__':sys.exit(run())
