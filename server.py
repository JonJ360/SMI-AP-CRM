"""Local single-user AP planning. Never bind beyond loopback or expose this as production."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from datetime import datetime
import json,secrets,argparse
from ap import Store
from gp_extract import PRIVATE
ROOT=Path(__file__).resolve().parent

def create_server(data_dir=PRIVATE,port=8876):
 data_dir=Path(data_dir);data_dir.mkdir(parents=True,exist_ok=True)
 def current():
  snapshot=json.loads((data_dir/'snapshot.json').read_text(encoding='utf-8')) if (data_dir/'snapshot.json').exists() else dict(source='NO GP SNAPSHOT — extraction required',asof=None,rows=[],companies={})
  return snapshot,Store(data_dir/'workflow.sqlite3',snapshot['rows'])
 token=secrets.token_urlsafe(32)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def respond(self,status,data,kind='application/json'):
   body=json.dumps(data,ensure_ascii=False).encode() if kind=='application/json' else data
   self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");self.end_headers();self.wfile.write(body)
  def safe_host(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
  def do_GET(self):
   if not self.safe_host():return self.respond(403,{'error':'Loopback Host required'})
   u=urlsplit(self.path)
   if u.path in ('/','/app.js','/style.css','/check-runs.js'):
    file={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/check-runs.js':'check-runs.js'}[u.path]
    if not (ROOT/file).exists():return self.respond(404,{'error':'Asset missing'})
    return self.respond(200,(ROOT/file).read_bytes(),{'/':'text/html','/app.js':'text/javascript','/style.css':'text/css','/check-runs.js':'text/javascript'}[u.path])
   if u.path=='/api/state':
    try:
     company=parse_qs(u.query).get('company',['SMI'])[0];today=datetime.now().astimezone().date().isoformat()
     snapshot,store=current();view=store.view(company,today)
     return self.respond(200,{**view,'csrf':token,'company':company,'aging_asof':today,'source':snapshot['source'],'asof':snapshot.get('asof'),'source_info':snapshot.get('companies',{}).get(company,{}),'persistence':str(data_dir/'workflow.sqlite3')})
    except ValueError:return self.respond(400,{'error':'Invalid company'})
   return self.respond(404,{'error':'Not found'})
  def do_POST(self):
   origin=f'http://127.0.0.1:{self.server.server_port}'
   if not self.safe_host() or self.headers.get('Origin')!=origin or not secrets.compare_digest(self.headers.get('X-AP-CSRF',''),token):return self.respond(403,{'error':'Local same-origin token required'})
   if self.path!='/api/workflow':return self.respond(404,{'error':'Not found'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if size<1 or size>16000 or self.headers.get('Content-Type')!='application/json':raise ValueError()
    data=json.loads(self.rfile.read(size));snapshot,store=current();store.update(data['id'],data['patch'])
    return self.respond(200,{'saved':True})
   except (ValueError,KeyError,TypeError):return self.respond(400,{'error':'Invalid update, held document or nonpayable credit'})
 return ThreadingHTTPServer(('127.0.0.1',port),Handler)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8876);p.add_argument('--data-dir',type=Path,default=PRIVATE);args=p.parse_args()
 s=create_server(args.data_dir,args.port);print(f'AP local preview http://127.0.0.1:{s.server_port} (single user, no payment execution)',flush=True)
 try:s.serve_forever()
 except KeyboardInterrupt:pass
 finally:s.server_close()
