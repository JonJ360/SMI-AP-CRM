"""Isolated synthetic workflow E2E + read-only real snapshot screenshots."""
import unittest,tempfile,threading,json,sys,os
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
EVIDENCE=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'hermes'/'ap-crm'/'evidence'
class Browser(unittest.TestCase):
 def test_vendor_invoice_selection_hold_note_reload_mobile(self):
  EVIDENCE.mkdir(parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory() as d:
   rows=[dict(id='SMI:1:A',company='SMI',vendor_id='TEST1',vendor='TEST FIXTURE Vendor — NOT REAL',document='TEST-A',due='2026-10-01',cents=12345,original_cents=15000,gp_hold=False,doctype=1,terms='TEST',description='<img src=x onerror=alert(1)>',document_date='2026-09-01',voucher='A'),dict(id='SFAB:1:B',company='SFAB',vendor_id='TEST2',vendor='SFAB TEST ONLY',document='TEST-B',due='2026-11-01',cents=900,gp_hold=True,doctype=1)]
   Path(d,'snapshot.json').write_text(json.dumps({'source':'TEST FIXTURE — NOT GP','asof':'2026-10-12T12:00:00Z','companies':{},'rows':rows}))
   s=server.create_server(Path(d),0);t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
   try:
    with sync_playwright() as p:
     b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1440,'height':1000}); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     page.goto(f'http://127.0.0.1:{s.server_port}');page.get_by_role('button',name='Vendors',exact=True).click();page.get_by_role('button',name='TEST FIXTURE Vendor — NOT REAL',exact=True).click()
     page.get_by_role('button',name='TEST-A',exact=True).click();page.get_by_label('Planning note').fill('Verify freight — TEST ONLY');page.get_by_role('button',name='Save note').click();page.get_by_text('Note saved locally',exact=True).wait_for();page.get_by_role('button',name='Close invoice').click()
     page.get_by_label('Select TEST-A').check();page.get_by_text('$123.45',exact=True).first.wait_for();page.reload();page.get_by_role('button',name='Payment plan',exact=True).click();self.assertTrue(page.get_by_label('Select TEST-A').is_checked())
     page.get_by_role('button',name='TEST-A',exact=True).click();self.assertEqual(page.get_by_label('Planning note').input_value(),'Verify freight — TEST ONLY');self.assertEqual(page.locator('dialog img').count(),0)
     page.get_by_label('Local planning hold').check();page.get_by_role('button',name='Close invoice').click();page.get_by_text('No matching documents',exact=True).wait_for()
     page.get_by_role('button',name='SFAB',exact=True).click();page.get_by_role('button',name='Open invoices',exact=True).click();self.assertTrue(page.get_by_label('Select TEST-B').is_disabled())
     for width in (390,1440):
      page.set_viewport_size({'width':width,'height':950});self.assertTrue(page.evaluate('document.documentElement.scrollWidth<=innerWidth'));page.screenshot(path=str(EVIDENCE/f'fixture-{width}.png'),full_page=True)
     self.assertEqual(errors,[]);b.close()
   finally:s.shutdown();s.server_close();t.join()
if __name__=='__main__':unittest.main()
