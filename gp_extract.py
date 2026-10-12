"""Bounded, manually invoked, SELECT-only SMI/SFAB current AP extraction.
No import-time SQL, publisher, scheduler, arbitrary SQL, or credential export.
"""
import json, sys, os, hashlib
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from ap import signed_cents
import check_runs
ROOT=Path(__file__).resolve().parent
PRIVATE=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'hermes' / 'ap-crm'
QUERIES={
 'vendor_balances':"SELECT RTRIM(VENDORID) vendorid,CURRBLNC balance FROM dbo.PM00201 ORDER BY VENDORID",
 'functional_currency':"SELECT RTRIM(FUNLCURR) currency FROM dbo.MC40000",
 'open':"SELECT TOP (10001) RTRIM(p.VENDORID) vendorid,RTRIM(v.VENDNAME) vendor,RTRIM(p.VCHRNMBR) voucher,RTRIM(p.DOCNUMBR) document,p.DOCTYPE,p.DOCDATE,p.DUEDATE,p.DOCAMNT,p.CURTRXAM,p.HOLD,v.HOLD vendor_hold,v.VENDSTTS,RTRIM(p.PYMTRMID) terms,RTRIM(p.TRXDSCRN) description,RTRIM(p.CURNCYID) currency FROM dbo.PM20000 p LEFT JOIN dbo.PM00200 v ON p.VENDORID=v.VENDORID WHERE p.VOIDED=0 AND p.CURTRXAM<>0 ORDER BY p.DOCTYPE,p.VCHRNMBR",
 'control':"SELECT DOCTYPE,COUNT(*) n,SUM(CURTRXAM) amount FROM dbo.PM20000 WHERE VOIDED=0 AND CURTRXAM<>0 GROUP BY DOCTYPE ORDER BY DOCTYPE",
 'work_count':"SELECT COUNT(*) n FROM dbo.PM10000 WHERE DOCAMNT<>0 OR CURTRXAM<>0",
 'permissions':"SELECT source_table,HAS_PERMS_BY_NAME(source_table,'OBJECT','SELECT') sel,HAS_PERMS_BY_NAME(source_table,'OBJECT','INSERT') ins,HAS_PERMS_BY_NAME(source_table,'OBJECT','UPDATE') upd,HAS_PERMS_BY_NAME(source_table,'OBJECT','DELETE') del,HAS_PERMS_BY_NAME(source_table,'OBJECT','ALTER') alt,HAS_PERMS_BY_NAME(source_table,'OBJECT','CONTROL') ctl FROM (VALUES ('dbo.PM20000'),('dbo.PM00200'),('dbo.PM10000'),('dbo.PM00201'),('dbo.MC40000')) AS x(source_table)",
 'authority':"SELECT IS_SRVROLEMEMBER('sysadmin') sysadmin,HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER') control_server,HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CREATE TABLE') create_table,HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL') control_db"
}
def normalize(company,raw,control):
 if company not in ('SMI','SFAB'): raise ValueError('Company not allowlisted')
 if len(raw)>=10001 or len({(r['DOCTYPE'],r['voucher']) for r in raw})!=len(raw): raise ValueError('Capped or duplicate rows')
 if {r['DOCTYPE'] for r in raw}!={r['DOCTYPE'] for r in control}: raise ValueError('Type coverage differs')
 for c in control:
  group=[r for r in raw if r['DOCTYPE']==c['DOCTYPE']]
  if len(group)!=c['n'] or sum((Decimal(str(r['CURTRXAM'])) for r in group),Decimal(0))!=Decimal(str(c['amount'])): raise ValueError('Independent control mismatch')
 rows=[]
 for r in raw:
  if r['vendor'] is None or r['vendor_hold'] is None or r['VENDSTTS'] is None: raise ValueError('Missing vendor master')
  rows.append(dict(id=f"{company}:{r['DOCTYPE']}:{r['voucher']}",company=company,vendor_id=r['vendorid'],vendor=r['vendor'],document=r['document'],voucher=r['voucher'],doctype=r['DOCTYPE'],document_date=str(r['DOCDATE'])[:10],due=str(r['DUEDATE'])[:10],cents=signed_cents(r['DOCTYPE'],r['CURTRXAM']),original_cents=signed_cents(r['DOCTYPE'],r['DOCAMNT']),gp_hold=bool(r['HOLD'] or r['vendor_hold'] or r['VENDSTTS']!=1),invoice_hold=bool(r['HOLD']),vendor_hold=bool(r['vendor_hold']),vendor_status=r['VENDSTTS'],terms=r['terms'],description=r['description'],source_currency=r['currency']))
 return rows

def vendor_control(rows, balances):
 actual={}
 for r in rows: actual[r['vendor_id']]=actual.get(r['vendor_id'],0)+r['cents']
 expected={r['vendorid']:Decimal(str(r['balance']))*100 for r in balances}
 if len(expected)!=len(balances) or any(Decimal(actual.get(k,0))!=expected.get(k,Decimal(0)) for k in set(actual)|set(expected)): raise ValueError('PM00201 vendor control mismatch')
 return {'matched_vendors':len(actual),'difference_cents':0}

def fetch(cur,q):
 cur.execute(q); cols=[c[0] for c in cur.description]; return [dict(zip(cols,r)) for r in cur.fetchall()]

def main():
 # This module's reviewed connector resolves Windows Credential Manager in memory.
 sys.path.insert(0,str(ROOT.parent/'financial-statements'/'scripts'))
 import financial_sync as fs
 PRIVATE.mkdir(parents=True,exist_ok=True)
 start=datetime.now(timezone.utc).isoformat(); result=dict(source='GP SELECT-only snapshot',asof=start,rows=[],companies={},scope='Posted nonvoid PM20000 open balances; separate posted payment history in company check_runs metadata; work excluded; functional-currency amounts. No payments executed.')
 for code in ('SMI','SFAB'):
  co=next(c for c in fs.ACTIVE_COMPANIES if c.code==code)
  conn=fs.connect_company(co)
  try:
   conn.timeout=25;cur=conn.cursor()
   permissions=fetch(cur,QUERIES['permissions']); authority=fetch(cur,QUERIES['authority'])
   if len(permissions)!=5 or any(tuple(p[k] for k in ('sel','ins','upd','del','alt','ctl'))!=(1,0,0,0,0,0) for p in permissions) or any(v!=0 for v in authority[0].values()): raise ValueError('Read-only permission guard failed')
   raw=fetch(cur,QUERIES['open']); control=fetch(cur,QUERIES['control']); work=fetch(cur,QUERIES['work_count'])[0]['n']
   rows=normalize(code,raw,control)
   balances=fetch(cur,QUERIES['vendor_balances']); reconciliation=vendor_control(rows,balances)
   currency=fetch(cur,QUERIES['functional_currency'])
   if len(currency)!=1 or currency[0]['currency'] not in ('USD','Z-US$','US$'): raise ValueError('USD functional currency not verified')
   history=check_runs.extract(cur,code,fetch);check_runs.validate_history(history)
   if balances!=fetch(cur,QUERIES['vendor_balances']): raise ValueError('Vendor balances moved during read')
   if raw!=fetch(cur,QUERIES['open']) or control!=fetch(cur,QUERIES['control']):raise ValueError('Source moved during extraction; no promotion')
   result['rows']+=rows
   result['companies'][code]=dict(name=co.name,check_runs=history,functional_currency=currency[0]['currency'],vendor_reconciliation=reconciliation,count=len(rows),work_excluded_count=work,control=control,permissions=permissions,authority=authority,stable_reread=True,extracted_at=datetime.now(timezone.utc).isoformat(),raw_sha256=hashlib.sha256(json.dumps(raw,default=str,sort_keys=True).encode()).hexdigest())
   (PRIVATE/f'checkpoint-{code}.json').write_text(json.dumps({'raw':raw,'control':control},default=str),encoding='utf-8')
  finally:conn.close()
 result['completed_at']=datetime.now(timezone.utc).isoformat()
 result['query_sha256']=hashlib.sha256(json.dumps({'open_ap':QUERIES,'check_runs':check_runs.QUERIES},sort_keys=True).encode()).hexdigest()
 temp=PRIVATE/'snapshot.tmp'; temp.write_text(json.dumps(result,default=str),encoding='utf-8'); temp.replace(PRIVATE/'snapshot.json')
 print(json.dumps({'status':'verified','path':str(PRIVATE/'snapshot.json'),'companies':{k:{'rows':v['count'],'work_excluded':v['work_excluded_count']} for k,v in result['companies'].items()}}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'status':'blocked','error_type':type(e).__name__,'note':'Prior snapshot preserved; no publication. Driver details suppressed.'}));sys.exit(1)
