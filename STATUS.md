# AP publication

## Current scoped release — 2026-10-12
- User explicitly confirmed successful existing-session sign-in: “I checked, I'm in, it works.” This closes the outstanding signed-in access gap as **user-confirmed**, not a new automated authenticated-session test.
- Palette corrected from the actual deployed/canonical AR Collections source: blue-to-teal header, sand background/borders, warm text, teal active navigation, matching blue information and red hold/past-due states. AP geometry, typography, auth, accounting, backend and guarded refresh code unchanged.
- Headless Edge synthetic-fixture visual regression compares computed colors to AR and checks unchanged geometry at 1440, 768, 390 and 320px. Before/after screenshots are explicitly fixtures, not production data or an authenticated session.
- Current five-minute refresh operation supersedes historical manual-only statements below; see operations/REFRESH.md. Deployment proof and precise commit are in private AP-Publication-Evidence/palette/release.json after release verification.

## Historical initial publication (superseded where noted above)
Production URL: https://jonj360.github.io/SMI-AP-CRM/
Published separate static shell with Jon-only database RPC access. Real SMI 776/SFAB 107 document manual snapshot uploaded. No GP writes, payment execution, scheduler, AR/RS changes, or Storage buckets.
Live anonymous table and RPC requests denied 401. Tables owner-only ACL + forced RLS/no policies; both RPCs check exact verified Jon Auth UID. Seven regression tests and isolated PostgreSQL security/authorization tests pass. Login page renders with no data or JS errors. Actual signed-in Jon end-to-end verification remains pending. Source refresh is MANUAL.
Private release evidence: C:/Users/jonj/OneDrive/Hermes/Documents/AP-Publication-Evidence/.

## Historical local vertical slice checkpoint
Started 2026-10-12 12:30 Central (tool clock).
Scope: separate SMI/SFAB AP; AR unchanged; no production deployments/schema/auth/schedulers; GP SELECT only; no payment execution.
Canonical reference: sibling SMI-AR-CRM/index.html (ocean header, sidebar, KPI cards, tables, drawer). New blue/white app, independent state.
Discovery: business-repo parent had no AP project; bounded local-tools search found historical SEAMX/OZAK1 report, not SMI/SFAB app. Process audit found no AP-related python/node command. GP inventory guard latest completed. AR dirty untracked work preserved.
Verified local slice: Python local backend, private SQLite workflow persistence, read-only GP snapshot, browser UI. Parent reran all 7 tests successfully and executed tests/verify_real_browser.py against real SMI/SFAB snapshots successfully. SMI 776 documents and SFAB 107 documents; both vendor-balance reconciliations zero difference. Desktop and mobile screenshots inspected; mobile invoice table requires horizontal scrolling. Source placeholder due dates (1900-01-01) still need display cleanup.

Local preview: http://127.0.0.1:8876 (session-managed server, not an installed service). Private data and evidence: C:/Users/jonj/AppData/Local/hermes/ap-crm/. No production deployment, authentication, multiuser store, automatic refresh or hub card. Partial payments, scheduled payment runs, exports and historical payment detail remain unimplemented. No payments executed or GP writes.

Next release gates: final source/security review, missing workflows, scoped authentication/storage, singleton refresh, backup/restore and exact deployed verification. Never publish private GP snapshots in static assets. Parent verification completed 2026-10-12 approximately 12:44 Central.
