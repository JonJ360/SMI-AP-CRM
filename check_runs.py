"""Posted GP payment groups. No source/cloud writes; fixed SELECTs only."""
from decimal import Decimal
import hashlib,json

SCOPE_START='2026-01-01'
# Explicit, schema-verified common fields. Header grain stays separate from applies.
HEADER_COLUMNS='VCHRNMBR,VENDORID,DOCNUMBR,TRXSORCE,BACHNUMB,BCHSOURC,DOCDATE,POSTEDDT,PSTGDATE,VOIDPDATE,DOCAMNT,CURTRXAM,VOIDED,CORRCTN,PYENTTYP,Electronic,CHEKBKID,CARDNAME,CURNCYID,TRXDSCRN,VNDCHKNM'
ALL_HEADERS=' UNION ALL '.join("SELECT '"+t+"' source_table,"+(HEADER_COLUMNS.replace('VOIDPDATE','CAST(NULL AS datetime) VOIDPDATE') if t=='PM20000' else HEADER_COLUMNS)+' FROM dbo.'+t+' WHERE DOCTYPE=6' for t in ('PM20000','PM30200'))
# Include whole posting groups if any member has a current-year document/posting
# date; undated headers are retained separately. No future-date cutoff.
CTE="WITH all_p AS ("+ALL_HEADERS+"), eligible AS (SELECT TRXSORCE,VCHRNMBR FROM all_p WHERE DOCDATE>='20260101' OR POSTEDDT>='20260101' OR (DOCDATE<='19000101' AND POSTEDDT<='19000101')), p AS (SELECT source_table,"+HEADER_COLUMNS+" FROM all_p h WHERE EXISTS(SELECT 1 FROM eligible e WHERE (h.TRXSORCE<>'' AND h.TRXSORCE=e.TRXSORCE) OR h.VCHRNMBR=e.VCHRNMBR)) "
APP_COLUMNS="RTRIM(a.VCHRNMBR) voucher,RTRIM(a.VENDORID) vendor_id,RTRIM(a.APTVCHNM) target_voucher,a.APTODCTY target_type,RTRIM(a.APTODCNM) target_document,a.APTODCDT target_date,a.DATE1 apply_date,a.GLPOSTDT apply_gl_date,a.APPLDAMT amount,a.DISTKNAM discount,a.WROFAMNT writeoff,a.POSTED posted"
APP_FROM=" FROM dbo.{table} a WHERE a.DOCTYPE=6 AND a.POSTED=1 AND EXISTS(SELECT 1 FROM p WHERE p.VCHRNMBR=a.VCHRNMBR AND p.VENDORID=a.VENDORID)"
APPS=' UNION ALL '.join("SELECT '"+t+"' source_table,"+APP_COLUMNS+APP_FROM.format(table=t) for t in ('PM10200','PM30300'))
QUERIES={
 'headers':CTE+"SELECT TOP (30001) p.source_table,RTRIM(p.VCHRNMBR) voucher,RTRIM(p.VENDORID) vendor_id,RTRIM(v.VENDNAME) vendor,RTRIM(p.DOCNUMBR) document,RTRIM(p.TRXSORCE) audit,RTRIM(p.BACHNUMB) batch,RTRIM(p.BCHSOURC) batch_source,p.DOCDATE document_date,p.POSTEDDT posted_date,p.PSTGDATE gl_date,p.VOIDPDATE void_date,p.DOCAMNT amount,p.CURTRXAM remaining,p.VOIDED voided,p.CORRCTN correction,p.PYENTTYP payment_type,p.Electronic electronic,RTRIM(p.CHEKBKID) checkbook,RTRIM(p.CARDNAME) card,RTRIM(p.CURNCYID) currency,RTRIM(p.TRXDSCRN) description,RTRIM(p.VNDCHKNM) payee FROM p LEFT JOIN dbo.PM00200 v ON p.VENDORID=v.VENDORID ORDER BY p.VCHRNMBR,p.source_table",
 'applications':CTE+", a AS ("+APPS+") SELECT TOP (60001) source_table,voucher,vendor_id,target_voucher,target_type,target_document,target_date,apply_date,apply_gl_date,amount,discount,writeoff,posted FROM a ORDER BY voucher,target_type,target_voucher,source_table",
 'header_control':CTE+"SELECT source_table,VOIDED voided,PYENTTYP payment_type,COUNT(*) n,SUM(DOCAMNT) amount,SUM(CURTRXAM) remaining FROM p GROUP BY source_table,VOIDED,PYENTTYP ORDER BY source_table,VOIDED,PYENTTYP",
 'apply_control':CTE+", a AS ("+APPS+") SELECT source_table,COUNT(*) n,SUM(amount) amount,SUM(discount) discount,SUM(writeoff) writeoff FROM a GROUP BY source_table ORDER BY source_table",
 'scope':"WITH all_p AS ("+ALL_HEADERS+") SELECT COUNT(*) n,MIN(CASE WHEN DOCDATE>'19000101' THEN DOCDATE END) first_document_date,MAX(DOCDATE) last_document_date,MIN(CASE WHEN POSTEDDT>'19000101' THEN POSTEDDT END) first_posted_date,MAX(POSTEDDT) last_posted_date FROM all_p",
 'permissions':"SELECT source_table,HAS_PERMS_BY_NAME(source_table,'OBJECT','SELECT') sel,HAS_PERMS_BY_NAME(source_table,'OBJECT','INSERT') ins,HAS_PERMS_BY_NAME(source_table,'OBJECT','UPDATE') upd,HAS_PERMS_BY_NAME(source_table,'OBJECT','DELETE') del,HAS_PERMS_BY_NAME(source_table,'OBJECT','ALTER') alt,HAS_PERMS_BY_NAME(source_table,'OBJECT','CONTROL') ctl FROM (VALUES ('dbo.PM20000'),('dbo.PM30200'),('dbo.PM10200'),('dbo.PM30300'),('dbo.PM00200')) x(source_table)"
}
def check_controls(headers,apps,hc,ac):
 if len(headers)>=30001 or len(apps)>=60001:raise ValueError('History extraction cap reached')
 for rows,controls,keys,amounts in ((headers,hc,('source_table','voided','payment_type'),('amount','remaining')),(apps,ac,('source_table',),('amount','discount','writeoff'))):
  if len(rows)!=sum(c['n'] for c in controls):raise ValueError('History count control')
  actual={}
  for r in rows:
   k=tuple(r[f] for f in keys);g=actual.setdefault(k,dict(n=0,**{a:Decimal(0) for a in amounts}));g['n']+=1
   for a in amounts:g[a]+=Decimal(str(r[a]))
  if len(actual)!=len(controls):raise ValueError('History control coverage')
  for c in controls:
   g=actual.get(tuple(c[f] for f in keys))
   if not g or g['n']!=c['n'] or any(g[a]!=Decimal(str(c[a])) for a in amounts):raise ValueError('History amount control')
def extract(cur,company,fetch):
 permissions=fetch(cur,QUERIES['permissions'])
 if len(permissions)!=5 or any(tuple(p[k] for k in ('sel','ins','upd','del','alt','ctl'))!=(1,0,0,0,0,0) for p in permissions):raise ValueError('History read-only guard')
 raw={k:fetch(cur,QUERIES[k]) for k in ('headers','applications','header_control','apply_control','scope')}
 check_controls(raw['headers'],raw['applications'],raw['header_control'],raw['apply_control'])
 for k,v in raw.items():
  if v!=fetch(cur,QUERIES[k]):raise ValueError('History moved during extraction')
 h=normalize(company,raw['headers'],raw['applications'])
 scope=raw['scope'][0]
 h['scope']=dict(start=SCOPE_START,basis='Whole posting groups with any payment document or posted-on date from 2026-01-01; undated payments included; future-dated documents included.',retained_payment_count=scope['n'],older_excluded_count=scope['n']-len(raw['headers']),retained_first_document_date=date(scope['first_document_date']),retained_last_document_date=date(scope['last_document_date']),retained_first_posted_date=date(scope['first_posted_date']),retained_last_posted_date=date(scope['last_posted_date']))
 h['reconciliation'].update(header_control_difference_cents=0,application_control_difference_cents=0,stable_reread=True)
 h['query_sha256']=hashlib.sha256(json.dumps(QUERIES,sort_keys=True).encode()).hexdigest()
 return h

def validate_history(h):
 try:
  pp=h['payments'];rr=h['runs'];c=h['reconciliation'];scope=h['scope']
  if len({p['id'] for p in pp})!=len(pp) or len({r['id'] for r in rr})!=len(rr):raise ValueError('History identity')
  if scope['retained_payment_count']!=len(pp)+scope['older_excluded_count'] or scope['start']!=SCOPE_START:raise ValueError('History scope')
  if not c['stable_reread'] or any(c[k]!=0 for k in ('group_difference_cents','header_control_difference_cents','application_control_difference_cents','bridge_exception_count','bridge_difference_cents')):raise ValueError('History controls')
  if c['payment_count']!=len(pp) or c['application_count']!=sum(len(p['applications']) for p in pp):raise ValueError('History counts')
  if sum(r['payment_count'] for r in rr)!=len(pp) or set(p['run_id'] for p in pp)!=set(r['id'] for r in rr):raise ValueError('Group coverage')
  for p in pp:
   cash=p['amount_cents'] if not p['voided'] and p['payment_type'] in (0,1,3) else 0
   if p['cash_cents']!=cash or p['applied_cents']!=sum(a['amount_cents'] for a in p['applications']):raise ValueError('Cash/app bridge')
   diff=None if p['voided'] else p['amount_cents']-p['remaining_cents']-p['applied_cents']
   if diff!=p['bridge_difference_cents']:raise ValueError('Application residual')
  for r in rr:
   group=[p for p in pp if p['run_id']==r['id']]
   if r['payment_count']!=len(group) or r['cash_cents']!=sum(p['cash_cents'] for p in group):raise ValueError('Run total')
  if c['cash_cents']!=sum(p['cash_cents'] for p in pp) or c['bridge_exception_count']!=sum(p['bridge_difference_cents'] not in (0,None) for p in pp):raise ValueError('History totals')
 except (KeyError,TypeError):raise ValueError('History contract incomplete') from None

def cents(v):
 n=Decimal(str(v))*100
 if n!=n.to_integral_value():raise ValueError('Fractional-cent payment amount')
 return int(n)
def date(v):
 s=str(v)[:10] if v else None
 return s if s and s>'1900-01-01' else None
def normalize(company,headers,applications):
 if company not in ('SMI','SFAB'):raise ValueError('Company')
 payments=[];runs={};seen=set()
 for raw in headers:
  p=dict(raw);key=(p['voucher'],p['vendor_id'])
  if key in seen:raise ValueError('Duplicate payment lifecycle')
  seen.add(key);p['id']=company+':6:'+p['voucher']
  for k in ('document_date','posted_date','gl_date','void_date'):p[k]=date(p[k])
  p['amount_cents']=cents(p.pop('amount'));p['remaining_cents']=cents(p.pop('remaining'))
  # TRXSORCE is a GP posting audit identifier, not a date or reusable batch name.
  identity=[company,p['audit']] if p['audit'] else [company,'unknown',p['id']]
  p['run_id']=hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
  p['cash_cents']=p['amount_cents'] if not p['voided'] and p['payment_type'] in (0,1,3) else 0
  r=runs.setdefault(p['run_id'],dict(id=p['run_id'],audit=p['audit'],cash_cents=0,payment_count=0))
  r['cash_cents']+=p['cash_cents'];r['payment_count']+=1;payments.append(p)
 by_key={(p['voucher'],p['vendor_id']):p for p in payments};applied_keys={};duplicate_apps=0
 for p in payments:p['applications']=[]
 for raw in applications:
  a=dict(raw);key=(a.pop('voucher'),a.pop('vendor_id'))
  if key not in by_key:raise ValueError('Orphan application')
  ak=(*key,a['target_type'],a['target_voucher'])
  comparable={k:v for k,v in a.items() if k!='source_table'}
  if ak in applied_keys:
   old,table=applied_keys[ak]
   if old!=comparable or table==a['source_table']:raise ValueError('Conflicting application lifecycle')
   duplicate_apps+=1;continue
  applied_keys[ak]=(comparable,a['source_table'])
  if a['posted']!=1:raise ValueError('Unposted application')
  for k in ('target_date','apply_date','apply_gl_date'):a[k]=date(a[k])
  for k in ('amount','discount','writeoff'):a[k+'_cents']=cents(a.pop(k))
  by_key[key]['applications'].append(a)
 for p in payments:
  p['applied_cents']=sum(a['amount_cents'] for a in p['applications'])
  p['discount_cents']=sum(a['discount_cents'] for a in p['applications'])
  p['writeoff_cents']=sum(a['writeoff_cents'] for a in p['applications'])
  p['bridge_difference_cents']=None if p['voided'] else p['amount_cents']-p['remaining_cents']-p['applied_cents']
  p['status']='Voided' if p['voided'] else 'Correction flagged' if p['correction'] else 'Not voided'
  p['payment_type_label']={0:'Check',1:'Cash',2:'Credit card (noncash)',3:'EFT'}.get(p['payment_type'],'Unknown code '+str(p['payment_type']))
  if p['electronic']:p['payment_type_label']+=' · electronic flag'
 for r in runs.values():
  pp=[p for p in payments if p['run_id']==r['id']]
  for key,out in [('batch','batches'),('batch_source','sources'),('checkbook','checkbooks'),('payment_type_label','payment_types')]:r[out]=sorted({p[key] for p in pp})
  for key in ('document_date','posted_date','gl_date'):
   dates=sorted({p[key] for p in pp if p[key]});r[key+'_min']=dates[0] if dates else None;r[key+'_max']=dates[-1] if dates else None
   r[key+'_unknown_count']=sum(p[key] is None for p in pp)
  r['original_cents']=sum(p['amount_cents'] for p in pp)
  r['void_cents']=sum(p['amount_cents'] for p in pp if p['voided']);r['void_count']=sum(bool(p['voided']) for p in pp)
  r['noncash_cents']=sum(p['amount_cents'] for p in pp if not p['voided'] and p['payment_type'] not in (0,1,3))
  r['bridge_exceptions']=sum(p['bridge_difference_cents'] not in (0,None) for p in pp)
  r['identity_basis']='GP posting audit group' if r['audit'] else 'Unknown run — individual payment'
 reconciliation=dict(group_difference_cents=sum(r['cash_cents'] for r in runs.values())-sum(p['cash_cents'] for p in payments),payment_count=len(payments),application_count=len(applications),cash_cents=sum(p['cash_cents'] for p in payments),bridge_exception_count=sum(p['bridge_difference_cents'] not in (0,None) for p in payments),bridge_difference_cents=sum(p['bridge_difference_cents'] or 0 for p in payments),void_count=sum(bool(p['voided']) for p in payments))
 return dict(runs=list(runs.values()),payments=payments,reconciliation={**reconciliation,'raw_application_count':len(applications),'application_count':len(applications)-duplicate_apps,'duplicate_application_rows_removed':duplicate_apps})
