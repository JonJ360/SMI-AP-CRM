"""Hash-fenced scheduled entrypoint; durable sanitized failure receipts."""
import hashlib,json,os,runpy,sys
from pathlib import Path
from datetime import datetime,timezone
PRIVATE=Path(os.environ['LOCALAPPDATA'])/'hermes/ap-crm'
def verify(manifest):
 for path,want in manifest['files'].items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=want: raise ValueError('Reviewed source hash changed')
def main():
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
