"""Read-only browser verification of local real GP snapshot. No workflow mutations."""
from pathlib import Path
import json,sys
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gp_extract import PRIVATE
out=PRIVATE/'evidence';out.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8876');page.wait_for_function("document.querySelector('#source').textContent.includes('GP SELECT-only snapshot')")
 for company in ('SMI','SFAB'):
  page.get_by_role('button',name=company,exact=True).click();page.wait_for_function('(c)=>document.querySelector("#company-name").textContent.startsWith(c)',arg=company)
  state=page.request.get('http://127.0.0.1:8876/api/state?company='+company).json()
  assert state['source']=='GP SELECT-only snapshot' and state['rows']
  assert all(r['company']==company for r in state['rows'])
  assert sum(r['cents'] for r in state['rows'])==state['net_cents']
  assert state['source_info']['vendor_reconciliation']['difference_cents']==0
  page.get_by_role('button',name='Dashboard',exact=True).click();page.screenshot(path=str(out/f'real-{company}-dashboard.png'),full_page=True)
  page.get_by_role('button',name='Vendors',exact=True).click();page.locator('[data-vendor]').first.click();page.locator('[data-invoice]').first.click();assert page.locator('dialog').is_visible();page.screenshot(path=str(out/f'real-{company}-invoice.png'));page.get_by_role('button',name='Close invoice').click()
  page.get_by_role('button',name='Dashboard',exact=True).click();page.set_viewport_size({'width':390,'height':950});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(out/f'real-{company}-mobile.png'),full_page=True);page.set_viewport_size({'width':1440,'height':1100})
  results.append(dict(company=company,documents=len(state['rows']),vendor_reconciliation=state['source_info']['vendor_reconciliation'],functional_currency=state['source_info']['functional_currency'],screenshot=str(out/f'real-{company}-dashboard.png')))
 assert not errors,errors
 b.close()
(out/'browser-verification.json').write_text(json.dumps({'status':'passed','mode':'read-only real GP snapshot; no live GP queries from browser','companies':results,'console_errors':errors},indent=2),encoding='utf-8')
print(json.dumps({'status':'passed','companies':results,'evidence':str(out)},indent=2))
