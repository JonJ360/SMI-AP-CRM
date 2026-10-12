"""AP accounting rules. All amounts are integer functional-currency cents."""
from datetime import date
from decimal import Decimal
import sqlite3, json, hashlib
from contextlib import contextmanager
from datetime import datetime, timezone

def fingerprint(row):
 return hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()

class Store:
 def __init__(self,path,rows):
  self.path=path; self.rows=rows
  if len({r['id'] for r in rows})!=len(rows): raise ValueError('Duplicate source identity')
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS selection_source (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)')
   db.execute('CREATE TABLE IF NOT EXISTS workflow (id TEXT PRIMARY KEY, hold INTEGER NOT NULL, selected INTEGER NOT NULL, note TEXT NOT NULL)')
   db.execute('CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY, at TEXT, id TEXT, before_json TEXT, after_json TEXT)')
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.path,timeout=10); db.row_factory=sqlite3.Row
  try:
   with db: yield db
  finally: db.close()
 def audit(self):
  with self.db() as db: return [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY seq')]
 def update(self,key,patch):
  row=next((r for r in self.rows if r['id']==key),None)
  if row is None or set(patch)-{'hold','selected','note'}: raise ValueError('Unknown record or field')
  for k in ('hold','selected'):
   if k in patch and type(patch[k]) is not bool: raise ValueError('Expected boolean')
  if 'note' in patch and (not isinstance(patch['note'],str) or len(patch['note'])>2000): raise ValueError('Note maximum 2000 characters')
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   old=db.execute('SELECT hold,selected,note FROM workflow WHERE id=?',(key,)).fetchone()
   old=dict(old) if old else dict(hold=False,selected=False,note='')
   prior=db.execute('SELECT fingerprint FROM selection_source WHERE id=?',(key,)).fetchone()
   new={**old,**patch}
   if 'selected' not in patch and (not prior or prior['fingerprint']!=fingerprint(row)): new['selected']=False
   if patch.get('selected') and (new['hold'] or row['gp_hold'] or row['cents']<=0): raise ValueError('Held or credit documents cannot be selected')
   if new['hold'] or row['gp_hold'] or row['cents']<=0: new['selected']=False
   db.execute('INSERT OR REPLACE INTO selection_source VALUES (?,?)',(key,fingerprint(row)))
   db.execute('INSERT OR REPLACE INTO workflow VALUES (?,?,?,?)',(key,int(new['hold']),int(new['selected']),new['note']))
   db.execute('INSERT INTO audit(at,id,before_json,after_json) VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),key,json.dumps(old),json.dumps(new)))
 def view(self,company,asof):
  if company not in ('SMI','SFAB'): raise ValueError('Company must be SMI or SFAB')
  with self.db() as db:
   state={r['id']:dict(r) for r in db.execute('SELECT * FROM workflow')}
   fingerprints={r['id']:r['fingerprint'] for r in db.execute('SELECT * FROM selection_source')}
  rows=[]
  for source in self.rows:
   if source['company']!=company: continue
   s=state.get(source['id'],{}); held=source['gp_hold'] or bool(s.get('hold'))
   rows.append({**source,'hold':bool(s.get('hold')),'held':held,'selected':bool(s.get('selected')) and fingerprints.get(source['id'])==fingerprint(source) and not held and source['cents']>0,'note':s.get('note',''),'aging':aging(source.get('due'),asof) if source['cents']>0 else 'Credit / payment'})
  return dict(rows=rows,net_cents=sum(r['cents'] for r in rows),gross_cents=sum(r['cents'] for r in rows if r['cents']>0),credit_cents=sum(r['cents'] for r in rows if r['cents']<0),selected_cents=sum(r['cents'] for r in rows if r['selected']))

def aging(due, asof):
 if not due or str(due)[:10] <= '1900-01-01': return 'Unknown'
 days=(date.fromisoformat(asof[:10])-date.fromisoformat(due[:10])).days
 return 'Current' if days<=0 else '1–30' if days<=30 else '31–60' if days<=60 else '61–90' if days<=90 else '91+'

def signed_cents(doctype, value):
 n=Decimal(str(value))*100
 if doctype not in range(1,7) or not n.is_finite() or n<0 or n!=n.to_integral_value(): raise ValueError('Unsupported document type, negative magnitude or subcent amount')
 return int(n)*(1 if doctype<=3 else -1)
