# Posted Check Runs

Read-only posted payment history for SMI/SFAB, separately from open AP and planning selections. No payment execution or GP writes.

## Source contract
- Headers: PM20000 + PM30200, DOCTYPE=6. Applications: PM10200 + PM30300, DOCTYPE=6 and POSTED=1; not PM20100.
- Group identity is company + TRXSORCE posting audit ID. Batch labels and dates are not unique. Missing audit IDs remain individual unknown-run payments.
- Load whole posting groups when any member has document or posted-on date >=2026-01-01; retain undated/future payments and explicitly disclose older excluded retained history.
- Keep DOCDATE, POSTEDDT, PSTGDATE, DATE1 and GLPOSTDT distinct. PM20000 lacks VOIDPDATE: unknown, not invented. Reversal linkage/bank clearing is not inferred.
- Cash totals use nonvoid payment headers for check/cash/EFT; void originals and credit-card/unknown-type noncash amounts stay separate. Discounts/write-offs are not cash.
- Exact cross-lifecycle application duplicates are removed once; conflicting or same-table duplicates fail. Independent raw count/amount controls run before deduplication. Every nonvoid header-minus-remaining-minus-applied bridge must equal zero before publication.
- Fixed SELECTs, read-only privilege checks, row caps, stable double reads, independent controls and company identity guard fail closed. Open AP still separately reconciles to PM00201.

## Publication and UI
History travels in companies[company].check_runs through the existing ap_publish_checked/ap_read snapshot contract. Positional arrays are only transport compression: PostgreSQL reconstructs full JSON before atomic two-company publish. No new backend objects or grants. Full recursive readback validates all history. Source hashes include check_runs.py; never refresh the guard without reviewed tests. Existing notes, holds, selections and audit remain separate.

Check Runs has whole-group date filters (posted-on/check-date/GL-date), search, summary, payment detail and applied-document detail. Unknown/future dates and full-group semantics are explicit. Old snapshots lacking history display an unavailable message, leaving open AP unchanged. Existing palette/shared sign-in/exact-Jon backend restriction are preserved.

## Release gates
Run the complete Python suite, npm test, tests/refresh-security.mjs, Node shared-session tests and tests/transport.mjs (AP_TEST_PYTHON selects the venv). Restore a real private backup with tests/restore-private.mjs. Exercise both companies and old-snapshot fallback in Edge. Verify guarded entrypoint, scheduled manual run and natural run, exact live payload equality, workflow/audit preservation, source manifest and all Pages assets built from the immutable commit.

Do not put business payloads in Git/Pages. Private run receipts and backups remain under LOCALAPPDATA/hermes/ap-crm; sanitized release evidence under OneDrive/Hermes/Documents/AP-Publication-Evidence/check-runs.
