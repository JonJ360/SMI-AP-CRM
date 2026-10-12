import importlib.util,unittest
class CheckRunsContract(unittest.TestCase):
 def test_posting_groups_not_batch_or_date(self):
  self.assertIsNotNone(importlib.util.find_spec('check_runs'),'Reviewed check run normalizer missing')
  from check_runs import normalize
  def p(v,a):
   return dict(voucher=v,vendor_id='V',vendor='Vendor',document=v,audit=a,batch='REUSED',batch_source='XPM_Cchecks',document_date='2026-01-02',posted_date='2026-01-03',gl_date='2026-01-02',void_date='1900-01-01',amount='100',remaining='100',voided=0,correction=0,payment_type=0,electronic=0,checkbook='BANK',card='',currency='USD',description='',payee='Vendor',source_table='PM20000')
  history=normalize('SMI',[p('1','A'),p('2','B'),p('3',''),p('4','')],[])
  self.assertEqual(len(history['runs']),4)
  self.assertEqual(sum(r['cash_cents'] for r in history['runs']),40000)
  self.assertEqual(history['payments'][0]['void_date'],None)
  self.assertEqual(history['reconciliation']['group_difference_cents'],0)
 def test_application_cash_bridge_and_voids(self):
  from check_runs import normalize
  base=dict(voucher='1',vendor_id='V',vendor='Vendor',document='CHECK',audit='A',batch='B',batch_source='XPM_Cchecks',document_date='2026-01-02',posted_date='2026-01-03',gl_date='2026-01-02',void_date='1900-01-01',amount='100',remaining='10',voided=0,correction=0,payment_type=0,electronic=0,checkbook='BANK',card='',currency='USD',description='',payee='',source_table='PM20000')
  app=dict(voucher='1',vendor_id='V',target_voucher='I',target_type=1,target_document='INV',target_date='2025-12-01',apply_date='2026-01-02',apply_gl_date='2026-01-02',amount='90',discount='5',writeoff='0',source_table='PM10200',posted=1)
  h=normalize('SMI',[base],[app]);p=h['payments'][0]
  both=normalize('SMI',[base],[app,{**app,'source_table':'PM30300'}])
  self.assertEqual(both['reconciliation']['duplicate_application_rows_removed'],1)
  self.assertEqual(both['payments'][0]['applied_cents'],9000)
  with self.assertRaises(ValueError):normalize('SMI',[base],[app,{**app,'source_table':'PM30300','amount':'89'}])
  self.assertEqual(p['cash_cents'],10000)
  self.assertEqual(p['applied_cents'],9000)
  self.assertEqual(p['discount_cents'],500)
  self.assertEqual(p['bridge_difference_cents'],0)
  self.assertEqual(len(p['applications']),1)
  void=normalize('SMI',[{**base,'voided':1,'remaining':'0'}],[])
  self.assertEqual(void['payments'][0]['cash_cents'],0)
  self.assertIsNone(void['payments'][0]['bridge_difference_cents'])
  cc=normalize('SMI',[{**base,'payment_type':2}],[app])
  self.assertEqual(cc['payments'][0]['cash_cents'],0)
 def test_extraction_is_fixed_bounded_and_reconciled(self):
  import check_runs as c
  self.assertTrue(hasattr(c,'QUERIES'),'Reviewed fixed SELECTs required')
  self.assertEqual(c.SCOPE_START,'2026-01-01')
  self.assertIn('PM10200',c.QUERIES['applications'])
  self.assertIn('PM30300',c.QUERIES['applications'])
  self.assertNotIn('PM20100',c.QUERIES['applications'])
  self.assertIn('TRXSORCE',c.QUERIES['headers'])
  self.assertIn('POSTED=1',c.QUERIES['applications'])
  self.assertIn('CAST(NULL AS datetime) VOIDPDATE',c.ALL_HEADERS)
  with self.assertRaises(ValueError):c.check_controls([],[],[{'n':1}],[])
 def test_history_publication_requires_validated_module_and_guard(self):
  import ap_refresh,gp_extract
  from pathlib import Path
  self.assertIn('check_runs.extract',Path(gp_extract.__file__).read_text())
  self.assertIn('check_runs.py',Path('operations/register-refresh.ps1').read_text())
  import check_runs as c
  with self.assertRaises(ValueError):c.validate_history({'runs':[],'payments':[],'reconciliation':{}})
 def test_duplicate_and_orphan_bridges_fail(self):
  from check_runs import normalize
  with self.assertRaises(ValueError):normalize('SMI',[],[{'voucher':'missing','vendor_id':'V'}])
