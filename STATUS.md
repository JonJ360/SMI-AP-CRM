# AP local vertical slice checkpoint
Started 2026-10-12 12:30 Central (tool clock).
Scope: separate SMI/SFAB AP; AR unchanged; no production deployments/schema/auth/schedulers; GP SELECT only; no payment execution.
Canonical reference: sibling SMI-AR-CRM/index.html (ocean header, sidebar, KPI cards, tables, drawer). New blue/white app, independent state.
Discovery: business-repo parent had no AP project; bounded local-tools search found historical SEAMX/OZAK1 report, not SMI/SFAB app. Process audit found no AP-related python/node command. GP inventory guard latest completed. AR dirty untracked work preserved.
Verified local slice: Python local backend, private SQLite workflow persistence, read-only GP snapshot, browser UI. Parent reran all 7 tests successfully and executed tests/verify_real_browser.py against real SMI/SFAB snapshots successfully. SMI 776 documents and SFAB 107 documents; both vendor-balance reconciliations zero difference. Desktop and mobile screenshots inspected; mobile invoice table requires horizontal scrolling. Source placeholder due dates (1900-01-01) still need display cleanup.

Local preview: http://127.0.0.1:8876 (session-managed server, not an installed service). Private data and evidence: C:/Users/jonj/AppData/Local/hermes/ap-crm/. No production deployment, authentication, multiuser store, automatic refresh or hub card. Partial payments, scheduled payment runs, exports and historical payment detail remain unimplemented. No payments executed or GP writes.

Next release gates: final source/security review, missing workflows, scoped authentication/storage, singleton refresh, backup/restore and exact deployed verification. Never publish private GP snapshots in static assets. Parent verification completed 2026-10-12 approximately 12:44 Central.
