"""Allowlist-only static publication; never copy snapshots or backend files."""
from pathlib import Path
import shutil
root=Path(__file__).parent
out=root/'site';out.mkdir(exist_ok=True)
for p in out.iterdir():
 if p.is_file():p.unlink()
html=(root/'index.html').read_text(encoding='utf-8').replace('href="/style.css"','href="./style.css"').replace('<script defer src="/app.js"></script>','<script defer src="./config.js"></script><script defer src="./cloud.js"></script><script defer src="./app.js"></script>').replace('LOCAL PREVIEW','JON ONLY').replace('<div class="layout">','<section id="auth" style="padding:2rem"><h1>Sign in to Accounts Payable</h1><p>Only Jon is authorized. Use your existing 360 account.</p><form id="login"><label>Email <input id="email" type="email" value="jonj@360-llc.com" autocomplete="username" required></label><label>Password <input id="password" type="password" autocomplete="current-password" required></label><button type="submit">Sign in</button></form><p id="auth-error" role="alert"></p></section><div class="layout" hidden>').replace('</header>','<button id="logout" hidden>Sign out</button></header>').replace('Reload local snapshot','Reload cloud snapshot')
html=html.replace('<meta name="viewport"','<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; connect-src https://inhwadbibwkakacdvoxu.supabase.co; object-src \'none\'; base-uri \'none\'; form-action \'none\'"><meta name="referrer" content="no-referrer"><meta name="viewport"')
(out/'index.html').write_text(html,encoding='utf-8',newline='\n')
for f in ['app.js','style.css','cloud.js','config.js']:(out/f).write_text((root/f).read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
with (out/'style.css').open('a',encoding='utf-8',newline='\n') as f:f.write('\n[hidden]{display:none!important}\n')
(out/'.nojekyll').touch()
print('Static allowlist:',sorted(p.name for p in out.iterdir()))
