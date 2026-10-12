"""Check Runs navigation and read-only drilldown in the real app shell."""
import unittest,tempfile,threading,json
from pathlib import Path
from playwright.sync_api import sync_playwright
import server,check_runs
class CheckRunsBrowser(unittest.TestCase):
 def test_history_drilldown_filters_company_xss_and_no_writes(self):
  base=dict(voucher='1',vendor_id='V',vendor='Synthetic Vendor',document='SYNTH-CHECK',audit='PMCHK-TEST',batch='SYNTH BATCH',batch_source='XPM_Cchecks',document_date='2026-10-01',posted_date='2026-10-02',gl_date='2026-10-01',void_date='1900-01-01',amount='100',remaining='0',voided=0,correction=0,payment_type=0,electronic=0,checkbook='TEST BANK',card='',currency='USD',description='<img src=x onerror=alert(1)>',payee='',source_table='PM30200')
  app=dict(voucher='1',vendor_id='V',target_voucher='I',target_type=1,target_document='SYNTH-INVOICE',target_date='2026-09-01',apply_date='2026-10-01',apply_gl_date='2026-10-01',amount='100',discount='5',writeoff='0',source_table='PM30300',posted=1)
  h=check_runs.normalize('SMI',[base],[app]);h['scope']=dict(start='2026-01-01',basis='Synthetic test only',older_excluded_count=20,retained_first_document_date='2010-01-01',retained_payment_count=21)
  with tempfile.TemporaryDirectory() as d:
   Path(d,'snapshot.json').write_text(json.dumps(dict(source='TEST FIXTURE NOT GP',asof='2026-10-12T12:00:00Z',rows=[],companies={'SMI':{'check_runs':h},'SFAB':{'check_runs':{**h,'runs':[],'payments':[]}}})))
   s=server.create_server(Path(d),0);t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
   try:
    with sync_playwright() as pw:
     b=pw.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];writes=[]
     page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:writes.append(r.url) if r.method!='GET' else None)
     page.goto(f'http://127.0.0.1:{s.server_port}')
     self.assertEqual(page.locator('[data-view="Check Runs"]').count(),1,'Check Runs navigation required')
     page.locator('[data-view="Check Runs"]').click();page.locator('#cr-all').click()
     self.assertIn('SYNTH BATCH',page.locator('#cr-body').inner_text())
     page.locator('[data-cr-run]').first.click();page.locator('[data-cr-payment]').first.click()
     self.assertIn('SYNTH-INVOICE',page.locator('#cr-body').inner_text());self.assertIn('$5.00',page.locator('#cr-body').inner_text())
     self.assertEqual(page.locator('#cr-body img').count(),0)
     page.locator('#cr-back').click();page.locator('#cr-back').click()
     page.locator('#cr-search').fill('NO MATCH');self.assertIn('No matching',page.locator('#cr-body').inner_text());page.locator('#cr-search').fill('')
     for width in (390,1440):
      page.set_viewport_size({'width':width,'height':950});self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
     page.get_by_role('button',name='SFAB',exact=True).click();page.wait_for_function("()=>document.querySelector('#company-name').textContent.startsWith('SFAB')")
     self.assertIn('No matching',page.locator('#cr-body').inner_text())
     page.locator('[data-view="Dashboard"]').click();self.assertTrue(page.locator('#cards').is_visible());self.assertFalse(page.locator('#check-runs').is_visible())
     Path(d,'snapshot.json').write_text(json.dumps(dict(source='OLD SNAPSHOT FIXTURE',asof='2026-10-12T12:00:00Z',rows=[],companies={'SMI':{},'SFAB':{}})))
     page.reload();page.locator('[data-view="Check Runs"]').click();self.assertIn('not available in this snapshot',page.locator('#check-runs').inner_text())
     self.assertEqual(errors,[]);self.assertEqual(writes,[]);b.close()
   finally:s.shutdown();s.server_close();t.join()
