"""Hash-fenced scheduled entrypoint; durable sanitized failure receipts."""
import hashlib,json,os,runpy,sys
from pathlib import Path
from datetime import datetime,timezone
PRIVATE=Path(os.environ['LOCALAPPDATA'])/'hermes/ap-crm'
def verify(manifest):
 for path,want in manifest['files'].items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=want: raise ValueError('Reviewed source hash changed')
def configure_windowless_subprocesses():
 """Keep console children of this scheduled worker off the user's desktop.

 pythonw hides only itself. Imports in the auth/client stack can still launch
 git or cmd.exe; apply this process-local default before importing that stack.
 No shared library, other task, command arguments or security guard is changed.
 """
 if sys.platform != 'win32':return
 import subprocess
 if getattr(subprocess.Popen,'_ap_windowless',False):return
 class WindowlessPopen(subprocess.Popen):
  _ap_windowless=True
  def __init__(self,*args,**kwargs):
   kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
   super().__init__(*args,**kwargs)
 subprocess.Popen=WindowlessPopen

def main():
 configure_windowless_subprocesses()
 try:
  manifest=json.loads((PRIVATE/'deployment.json').read_text());verify(manifest)
 except Exception as e:
  receipt={'status':'blocked','error_type':type(e).__name__,'reason':'Deployment/source guard failed','at':datetime.now(timezone.utc).isoformat()}
  with (PRIVATE/'source-guard-failures.jsonl').open('a') as f:f.write(json.dumps(receipt)+'\n')
  return 1
 sys.path.insert(0,str(Path(manifest['entrypoint']).parent))
 import ap_refresh
 return ap_refresh.run()
if __name__=='__main__':sys.exit(main())
