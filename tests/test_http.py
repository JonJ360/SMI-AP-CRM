"""Real loopback HTTP tests. All workflow writes use synthetic isolated data."""
import unittest,tempfile,threading,json,urllib.request,urllib.error,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
class HTTP(unittest.TestCase):
 def test_http_scope_and_mutation_security(self):
  with tempfile.TemporaryDirectory() as d:
   snapshot={'source':'TEST FIXTURE — NOT GP','asof':'2026-10-12T12:00:00Z','companies':{},'rows':[]}
   Path(d,'snapshot.json').write_text(json.dumps(snapshot))
   s=server.create_server(Path(d),0); t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
   base=f'http://127.0.0.1:{s.server_port}'
   try:
    self.assertIn(b'Accounts Payable',urllib.request.urlopen(base).read())
    data=json.load(urllib.request.urlopen(base+'/api/state?company=SMI'))
    self.assertEqual(data['rows'],[])
    self.assertIn('csrf',data)
    snapshot['source']='UPDATED TEST SNAPSHOT';Path(d,'snapshot.json').write_text(json.dumps(snapshot))
    self.assertEqual(json.load(urllib.request.urlopen(base+'/api/state?company=SMI'))['source'],'UPDATED TEST SNAPSHOT')
    for path,headers in [('/api/state?company=RSS',{}),('/../gp_extract.py',{}),('/api/state',{'Host':'evil.example'})]:
     with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(base+path,headers=headers))
    req=urllib.request.Request(base+'/api/workflow',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://evil.example'},method='POST')
    with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
    self.assertEqual(e.exception.code,403)
   finally:s.shutdown();s.server_close();t.join()
