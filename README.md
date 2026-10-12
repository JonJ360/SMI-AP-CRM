# SMI/SFAB Accounts Payable

Separate planning workspace. GP is read-only; no payment execution.

Production: GitHub Pages static allowlist built by `python build_site.py`; Supabase project `inhwadbibwkakacdvoxu`. Exact Jon Auth UID is enforced within both security-definer RPCs; all direct AP table/sequence privileges revoked except owner. Forced RLS with no policies. No storage buckets or additional data routes.

Database: `supabase/ap.sql`. `ap_read(text)` reads one company; `ap_update(text,text,jsonb)` changes planning note/hold/selection and records audit atomically. Source snapshot remains manual; reload does not query GP. Source changes invalidate prior selections.

Tests: `npm ci && npm test`; `python -m unittest discover -s tests -v`. Local preview remains loopback-only and is not the production backend.

Never commit snapshot.json, SQLite, credentials, or GP business rows. Publication builds only six static assets. Existing Windows snapshot remains private.
