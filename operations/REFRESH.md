# AP automatic GP refresh

Task `Hermes_APCRM_GP_Refresh` runs `scheduled_refresh.py` every five minutes as Jon, Interactive/Limited, IgnoreNew, maximum four minutes. This is deterministic Python, not a Hermes/LLM cron task. Requires workstation online, Jon logged in, GP LAN and existing renewable Supabase management authorization. Check Runs adds bounded retained posting-group history; measured full guarded history runs are approximately one minute. The task uses the same virtual environment’s windowless pythonw.exe to avoid an interactive console and console-close termination. No AR/RS scheduler or data changes.

## Safety and ownership

- Reviewed `gp_extract.py` performs only fixed SELECTs against SMI/SFAB; object/server permission guards, document amount/count controls, PM00201 vendor reconciliation, USD functional currency and stable double reads must pass. Zero/partial/capped/moved source fails closed.
- Private `deployment.json` hashes the entrypoint, refresh implementation, GP extractor, Check Runs module, accounting module, existing connector and OAuth renewal helper. Any source drift blocks scheduled execution until an operator reviews and runs `operations/register-refresh.ps1 -RefreshGuard`.
- Windows IgnoreNew plus a kernel-backed byte lock prevents concurrent CLI/task refreshes. PostgreSQL advisory transaction lock and fixed-order snapshot row locks serialize publishes against workflow updates.
- `ap_publish_checked` validates both companies, freshness and generation, retains both previous snapshots, publishes both companies and a durable count receipt in one database transaction. It never mutates human workflow/audit. Existing exact-Jon read/write RPCs retain source-fingerprint invalidation.
- All five AP tables are forced RLS, no policies/direct API-role privileges. Publisher is owner-only. No anonymous/authenticated/service-role ingestion grants or new identities. Existing profile-bound Supabase management OAuth is resolved/renewed in memory using the existing fenced provider. This credential remains project-management-capable, not an AP-scoped token; no existing AP-only noninteractive credential was available, and public/authenticated ingestion rights were deliberately not introduced. The runner's queries are fixed AP-only, but this is an application boundary rather than a claim that management credentials became least-privilege credentials.
- Large history is sent using positional wire encoding and reconstructed to the exact original JSON inside a SELECT expression before the unchanged atomic publisher. This avoids the management API request-size limit without schema/RPC/privilege changes. After publication, both full payloads are read back and compared recursively to the complete expected JSON, source timestamp, query hash and document counts before local promotion/success receipt.

## Private recovery and evidence

`%LOCALAPPDATA%/hermes/ap-crm/runs/<run-id>/` contains pre-publish gzip export of AP snapshot/workflow/audit, prior local snapshot, online SQLite workflow backup, extracted source and sanitized receipt. Data is NOT committed or sent to Pages. ACL verified Jon, SYSTEM and Administrators only. Cloud previous-known-good snapshot remains private. No automatic historical backup deletion is configured.

Every run restores its export into an isolated SQLite JSON target and verifies exact content/integrity. `node tests/restore-private.mjs <private cloud-backup.json.gz>` additionally rebuilds actual AP SQL schema in isolated in-memory PostgreSQL/PGlite, restores all records, compares full nested content, and tests exact-Jon reads/anonymous denial. This is not a live destructive restore, off-host backup, provider PITR guarantee or disaster-loss protection. Live workflow/audit happened to be empty during this drill; populated-note/selection/audit retention is separately tested using synthetic data in `tests/refresh-security.mjs`.

Sanitized evidence: `C:/Users/jonj/OneDrive/Hermes/Documents/AP-Publication-Evidence/refresh-*.json`; current private health receipt `%LOCALAPPDATA%/hermes/ap-crm/latest-receipt.json`. Source guard failures append `source-guard-failures.jsonl`. Failures preserve last good cloud/local data. No raw driver exceptions, OAuth tokens or credentials are logged.

## Verification commands

Use `C:/Users/jonj/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe`.

- `python -m unittest discover -s tests -v`
- `npm test && node tests/refresh-security.mjs`
- `python scheduled_refresh.py` — exact task entrypoint, a real GP extraction/publication
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File operations/register-refresh.ps1` — read task status only
- `-Install` creates only the AP task and refuses replacement. `-RefreshGuard` changes only reviewed local source hashes, not schedule.

UI describes automatic five-minute refresh, explicit workstation dependency, and flags snapshots >=15 minutes old. Reload reads the last verified snapshot, not GP directly.
