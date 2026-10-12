"""Allowlist-only static publication; never copy snapshots or backend files."""
from pathlib import Path
import shutil
root=Path(__file__).parent
out=root/'site';out.mkdir(exist_ok=True)
for p in out.iterdir():
 if p.is_file():p.unlink()
html=(root/'index.html').read_text(encoding='utf-8').replace('href="/style.css"','href="./style.css"').replace('src="/check-runs.js"','src="./check-runs.js"').replace('<script defer src="/app.js"></script>','<script defer src="./config.js"></script><script defer src="./supabase.min.js"></script><script defer src="./shared-session.js"></script><script defer src="./cloud.js"></script><script defer src="./app.js"></script>').replace('LOCAL PREVIEW','JON ONLY').replace('<div class="layout">','<section id="auth" style="padding:2rem"><h1>Accounts Payable · Jon only</h1><p>Using your existing 360 sign-in automatically. No separate AP password is needed.</p><p><a href="../SMI-AR-CRM/">AR Collections</a> · <a href="../assets/">Asset Register</a> · <a href="../apps/">360 Apps</a></p><button id="retry-session">Check existing session</button><p id="auth-error" role="alert"></p></section><div class="layout" hidden>').replace('</header>','<a href="../apps/">360 Apps</a></header>').replace('Reload local snapshot','Reload cloud snapshot')
html=html.replace('<meta name="viewport"','<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; connect-src https://inhwadbibwkakacdvoxu.supabase.co; object-src \'none\'; base-uri \'none\'; form-action \'none\'"><meta name="referrer" content="no-referrer"><meta name="viewport"')
(out/'index.html').write_text(html,encoding='utf-8',newline='\n')
for f in ['app.js','check-runs.js','style.css','cloud.js','config.js','shared-session.js','supabase.min.js']:(out/f).write_text((root/f).read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
with (out/'style.css').open('a',encoding='utf-8',newline='\n') as f:f.write('\n[hidden]{display:none!important}\n')
(out/'.nojekyll').touch()
print('Static allowlist:',sorted(p.name for p in out.iterdir()))
