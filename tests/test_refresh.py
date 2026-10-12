import unittest, importlib.util, tempfile, hashlib, subprocess, sys, os
from pathlib import Path
class RefreshContract(unittest.TestCase):
 def test_refresh_contract(self):
  self.assertIsNotNone(importlib.util.find_spec('ap_refresh'),'deterministic refresh module required')
  import ap_refresh as r
  with self.assertRaises(ValueError):r.validate({'companies':{},'rows':[]})
  self.assertEqual(r.PROJECT,'inhwadbibwkakacdvoxu')
  self.assertNotIn('ap_update',r.PUBLISH_SQL)
  self.assertNotIn('ap_workflow',r.PUBLISH_SQL)
 def test_source_hash_fails_closed(self):
  from scheduled_refresh import verify
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'source.py';p.write_text('approved')
   m={'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()}}
   verify(m);p.write_text('changed')
   with self.assertRaises(ValueError):verify(m)
 def test_singleton_skips_without_touching_backend(self):
  import msvcrt
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'refresh.lock'
   with p.open('w+b') as f:
    f.write(b'0');f.flush();f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    code="import ap_refresh;from pathlib import Path;ap_refresh.PRIVATE=Path("+repr(td)+");raise SystemExit(ap_refresh.run())"
    out=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=10)
    self.assertEqual(out.returncode,0,out.stderr.decode())
    self.assertEqual(list(Path(td).iterdir()),[p])
