"""Headless Edge visual regression. Synthetic UI only; never authenticates.
Usage: python tests/verify_palette.py before|after EVIDENCE_DIRECTORY AR_HTML
Build site/ first. The before CSS is frozen in EVIDENCE_DIRECTORY/before-style.css.
"""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
phase, dest, ar_path = sys.argv[1:]
OUT = Path(dest)
OUT.mkdir(parents=True, exist_ok=True)
css = (OUT / 'before-style.css').read_text() if phase == 'before' else (ROOT / 'site/style.css').read_text()
ar = Path(ar_path).read_text(encoding='utf-8')
# Only document-head CSS; script strings contain print-window <style> tags.
reference_css = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', ar.split('</head>', 1)[0], re.S))
fixture = dict(source='SYNTHETIC VISUAL FIXTURE — NOT LIVE GP / NOT SIGNED IN', asof='2026-10-12T18:00:00Z', aging_asof='2026-10-12', source_info=dict(name='TEST ONLY',work_excluded_count=0), net_cents=1234500, gross_cents=1254500, credit_cents=-20000, selected_cents=0, rows=[dict(id='SMI:1:FIXTURE', company='SMI', vendor_id='FIXTURE', vendor='Synthetic vendor — NOT REAL', document='FIXTURE-001', voucher='FIXTURE', cents=1254500, original_cents=1254500, due='2026-10-01', document_date='2026-09-01', aging='1–30', doctype=1, gp_hold=True, hold=False, held=True, note='', selected=False)])
bootstrap = 'window.apAPI={read:async()=>({ok:true,json:async()=>('+json.dumps(fixture)+')}),start:fn=>{document.querySelector("#auth").hidden=true;document.querySelector(".layout").hidden=false;fn();}};'
checks = [('header','backgroundImage','.bar'),('body','backgroundColor','body'),('body','color','body'),('.card','borderTopColor','.kcard'),('nav button:not(.active)','color','.nv'),('nav button.active','backgroundImage','.nv.on'),('nav button.active','color','.nv.on'),('nav button.active','borderTopColor','.nv.on'),('th','backgroundColor','.ctbl th'),('th','color','.ctbl th'),('.held','color','.nb.urg'),('.held','backgroundColor','.nb.urg'),('.held','borderTopColor','.nb.urg')]
result = {'phase':phase,'kind':'synthetic UI; not authenticated live session','viewports':[], 'assertions':[]}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    ref = browser.new_page()
    ref.set_content('<style>'+reference_css+'</style><div class="bar"></div><div class="kcard"></div><div class="nv"></div><div class="nv on"></div><table class="ctbl"><thead><tr><th>Test</th></tr></thead></table><span class="nb urg">Held</span>')
    expected = [ref.locator(sel).first.evaluate('(e,p)=>getComputedStyle(e)[p]', prop) for _, prop, sel in checks]
    page = browser.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def serve(route):
        name=route.request.url.split('/')[-1] or 'index.html'
        if name=='style.css': body=css; kind='text/css'
        elif name=='cloud.js': body=bootstrap; kind='text/javascript'
        elif name in ('config.js','supabase.min.js','shared-session.js'): body=''; kind='text/javascript'
        else: body=(ROOT/'site'/name).read_text(encoding='utf-8');kind='text/html' if name.endswith('.html') else 'text/javascript'
        route.fulfill(status=200,body=body,content_type=kind)
    page.route('http://fixture.test/**',serve)
    for width in (1440,390,320,768):
        page.set_viewport_size(dict(width=width,height=1000))
        page.goto('http://fixture.test/',wait_until='networkidle')
        page.locator('.card').first.wait_for()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        geometry=page.locator('header,aside,main,.card,.aging,.workspace,.plan-bar').evaluate_all('(es)=>es.map(e=>({tag:e.tagName,cls:e.className,x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))')
        result['viewports'].append({'width':width,'geometry':geometry,'document_overflow':False,'table_scroll_expected':page.locator('.table-wrap').evaluate('e=>e.scrollWidth>e.clientWidth')})
        if width in (1440,390): page.screenshot(path=str(OUT/f'{phase}-fixture-{width}.png'),full_page=True)
        if width==1440:
            for (sel, prop, _), value in zip(checks,expected):
                actual=page.locator(sel).first.evaluate('(e,p)=>getComputedStyle(e)[p]',prop)
                result['assertions'].append(dict(selector=sel,property=prop,expected=value,actual=actual,match=actual==value))
            page.get_by_role('button',name='FIXTURE-001',exact=True).click()
            page.screenshot(path=str(OUT/f'{phase}-fixture-dialog.png'),full_page=True)
    browser.close()
result['browser_errors']=errors
assert not errors,errors
(OUT/f'{phase}-computed.json').write_text(json.dumps(result,indent=2))
if phase=='after':
    assert all(a['match'] for a in result['assertions']),result['assertions']
    before=json.loads((OUT/'before-computed.json').read_text())
    assert [v['geometry'] for v in before['viewports']]==[v['geometry'] for v in result['viewports']], 'Layout geometry changed'
print(json.dumps({'phase':phase,'color_checks':len(checks),'matched':sum(a['match'] for a in result['assertions']),'viewports':len(result['viewports']),'errors':errors}))
