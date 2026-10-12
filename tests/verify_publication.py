"""Verify published bytes and anonymous denials; never acquire or fake user auth."""
import json,hashlib,requests,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('C:/Users/jonj/OneDrive/Hermes/Documents/AP-Publication-Evidence');OUT.mkdir(exist_ok=True)
config=json.loads((ROOT/'config.js').read_text().split('=',1)[1].strip().rstrip(';'))
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
url='https://jonj360.github.io/SMI-AP-CRM/'
result={'commit':commit,'url':url,'assets':[],'anonymous':[]}
for f in ['index.html','app.js','style.css','cloud.js','config.js']:
 r=requests.get(url+f+'?verify='+commit,timeout=45);r.raise_for_status()
 local=(ROOT/'site'/f).read_bytes()
 assert r.content==local,f+' byte mismatch'
 result['assets'].append({'file':f,'sha256':hashlib.sha256(local).hexdigest(),'status':r.status_code})
for table in ['ap_snapshot','ap_workflow','ap_audit']:
 r=requests.get(config['url']+'/rest/v1/'+table+'?select=*',headers={'apikey':config['key']},timeout=30)
 assert r.status_code in [401,403],(table,r.status_code)
 result['anonymous'].append({'object':table,'status':r.status_code})
for rpc,body in [('ap_read',{'p_company':'SMI'}),('ap_update',{'p_company':'SMI','p_id':'NONEXISTENT-SECURITY-PROBE','p_patch':{}})]:
 r=requests.post(config['url']+'/rest/v1/rpc/'+rpc,headers={'apikey':config['key']},json=body,timeout=30)
 assert r.status_code in [401,403],(rpc,r.status_code)
 result['anonymous'].append({'object':rpc,'status':r.status_code})
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url,wait_until='networkidle');assert page.locator('#auth').is_visible();assert not page.locator('.layout').is_visible();assert page.locator('#tbody').inner_text()==''
 page.screenshot(path=str(OUT/'published-login.png'),full_page=True)
 assert not errors,errors
 result['browser']={'login_visible':True,'data_hidden':True,'errors':errors,'authorized_session_test':'not performed — no existing safe Jon session acquired'}
 b.close()
(OUT/'publication.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
