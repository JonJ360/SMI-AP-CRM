import copy,hashlib,json,unittest
from datetime import datetime,timezone
import check_runs as c
import ap_refresh

def fixture(company='SMI'):
 p=dict(voucher='1',vendor_id='V',vendor='Synthetic',document='CHECK',audit='AUDIT',batch='B',batch_source='XPM_Cchecks',document_date='2026-01-02',posted_date='2026-01-03',gl_date='2026-01-02',void_date=None,amount='100',remaining='100',voided=0,correction=0,payment_type=0,electronic=0,checkbook='BANK',card='',currency='USD',description='',payee='',source_table='PM20000')
 h=c.normalize(company,[p],[])
 h['scope']=dict(start=c.SCOPE_START,retained_payment_count=1,older_excluded_count=0)
 h['reconciliation'].update(stable_reread=True,header_control_difference_cents=0,application_control_difference_cents=0)
 h['query_sha256']=hashlib.sha256(json.dumps(c.QUERIES,sort_keys=True).encode()).hexdigest()
 return h

class HistoryValidation(unittest.TestCase):
 def test_valid_and_tampered_history(self):
  h=fixture();c.validate_history(h)
  for section,key,value in [('reconciliation','payment_count',2),('reconciliation','cash_cents',0),('reconciliation','stable_reread',False),('scope','older_excluded_count',-1)]:
   bad=copy.deepcopy(h);bad[section][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):c.validate_history(bad)
  bad=copy.deepcopy(h);bad['payments'][0]['remaining_cents']=0;bad['payments'][0]['bridge_difference_cents']=10000;bad['runs'][0]['bridge_exceptions']=1;bad['reconciliation'].update(bridge_exception_count=1,bridge_difference_cents=10000)
  with self.assertRaises(ValueError):c.validate_history(bad)
 def test_publication_requires_history_and_company(self):
  s=dict(source='GP SELECT-only snapshot',asof=datetime.now(timezone.utc).isoformat(),rows=[dict(company=co,id=co+':1:INV') for co in ('SMI','SFAB')],companies={co:dict(count=1,stable_reread=True,vendor_reconciliation={'difference_cents':0},check_runs=fixture(co)) for co in ('SMI','SFAB')})
  ap_refresh.validate(s)
  bad=copy.deepcopy(s);del bad['companies']['SMI']['check_runs']
  with self.assertRaises(ValueError):ap_refresh.validate(bad)
  bad=copy.deepcopy(s);bad['companies']['SFAB']['check_runs']=fixture('SMI')
  with self.assertRaises(ValueError):ap_refresh.validate(bad)
