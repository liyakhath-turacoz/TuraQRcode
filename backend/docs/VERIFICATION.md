# TuraQRcode verification

Executed on **29 October 2026** in `E:\TuraQRcode`.

## Results

| Check | Result |
|---|---|
| Application layout | `backend`, `admin`, and `frontend` are independently runnable/buildable application folders. Subsequently consolidated under one root Git repository for the requested GitHub remote, with root README/deployment documentation. |
| Customer production build | Passed: TypeScript and Vite |
| Administrator production build | Passed: TypeScript and Vite |
| Backend/PostgreSQL test suite | 51 tests passed against isolated, genuine local PostgreSQL |
| Browser end-to-end suite | 12 scenarios passed in Chromium; 390 px mobile and 1280 px desktop coverage |
| Automated accessibility | No violations for the selected WCAG A/AA checks on public, account, workspace, and administrator activity pages |
| QR decoding | All seven content types, all three patterns with logos/frames, decoded with ZXing-C++ |
| Supabase connection | Passed with client-to-Supabase TLS verified through libpq |
| Supabase migrations | Revision `8904875a8d26` applied; eight application tables plus the Alembic version table |
| Supabase data isolation | Private `tura` schema; RLS enabled; Supabase anonymous/authenticated API roles denied schema access |
| Live persistence smoke | Registration, sessions, QR creation/read-back, redirect, scan reporting, downloads, role restriction, and deletion passed |
| Initial administrator | Exists server-side, Argon2id hash verified, administrator role verified, mandatory password change verified |
| npm audit | Zero known vulnerabilities in customer, administrator, and local database tooling dependencies |
| pip-audit | No known vulnerabilities in the installed Python environment |
| Combined startup command | Passed: `scripts/dev.py` started all three applications; actual customer home, registration, both sign-in screens, and Supabase API readiness passed with no browser runtime errors |

The live smoke account and its data were removed after testing. The real Supabase administrator’s temporary password was **not changed by tests**. Administrator password changes in browser tests occur only in the local `tura_e2e` database.

## Feature coverage

| Feature | Evidence |
|---|---|
| Registration and required policies | API rejects either missing consent; browser requires checkbox; timestamp and policy version persist |
| Sign-in/logout and profile | Correct/incorrect credentials, case normalization, session expiry, logout revocation, browser profile read-back |
| Password change and recovery | First-admin-login restriction, strong password validation, other-session revocation, invalid/expired/reused tokens, administrator-assisted browser recovery |
| Authorization | Member-to-admin rejection; cross-user read/edit/delete/download/export/analytics denial; role injection rejected |
| URL shortening and aliases | Custom slug resolution, collision rejection, short-link mode, immutable QR redirect address after destination updates |
| QR content | URL, exact plain text, email, telephone, SMS, Wi-Fi escaping/whitespace, UTF-8 SSID length, vCard |
| QR appearance | Colors/contrast, square/rounded/dot patterns, raster logo validation/normalization, frame; actual PNG decoding |
| Export formats | PNG, SVG, PDF signatures, browser downloads, ZIP content, A4 print PDF |
| Link controls | Pause/reactivate, expiration/clearing expiry, password form/wrong password/unlock/removal, mobile/desktop rule |
| Analytics | Distinct scan/click channels, counts, UTC daily aggregates, device categories, referrer-host redaction, CSV, top codes |
| Saved-code organization | Search, filters, pagination, alphabetical sort, deletion, safe project removal/unassignment |
| Business cards | Create/edit/delete, escaped public HTML, public profile, vCard, downloadable QR; browser flow verified |
| Bulk creation | CSV parsing/column mapping in browser; validation, alias conflicts, partial success without transaction corruption, ZIP/print |
| Administration | Counts, account search, suspension/session revocation, public-content suspension, restoration, code moderation, confidential recovery links, audit history |
| Request protection | Origin checks, login rate limiting, bounded mutation bodies, no password echo in validation errors |
| Scan reliability | Over-capacity static content is rejected before persistence; accessible contrast enforced for generated QR images |

## Commands to reproduce

Start local PostgreSQL from `backend/tools` with `npm ci` and `npm run db:local`. Then:

```powershell
# From backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip_audit --progress-spinner off
.venv\Scripts\python.exe scripts\supabase-smoke.py

# From frontend
npm run test:e2e
npm run build
npm audit

# From admin
npm run build
npm audit
```

Destructive tests refuse a non-loopback database. Pytest uses `tura_test`; browser tests use `tura_e2e` on 55432. The existing Supabase `.env` is not overwritten. Test HTML reports remain in `frontend/playwright-report`, and representative screenshots are in `frontend/tests/screenshots`.

## Configuration-dependent limits

- **Email delivery:** No SMTP credentials were supplied. Administrator-assisted recovery works and was tested; actual recovery-email delivery remains unverified until SMTP is configured.
- **Public deployment and branded domains:** Local browser tests do not establish public hosting, DNS, or HTTPS certificates. One deployment-level branded link hostname is supported by `PUBLIC_BASE_URL`; self-service per-user domain registration is outside the initial release. Configure a stable public hostname before printing dynamic codes.
- **Docker:** Docker/Nginx deployment files are included, but container deployment was not run because Docker Desktop was unavailable. Both static application builds and the API were tested directly.
- **Static QR behavior:** Static content cannot be edited or tracked after printing, and disabling/deleting a saved record cannot erase a downloaded static QR image. Managed-link controls apply to editable codes and short links.
- **Activity semantics:** Requests include repeat visits and bots; reports do not claim unique people, precise locations, or verified human scans. CSV exports include at most 50,000 activity rows per request.
- **Accessibility:** Automated selected WCAG checks and keyboard-friendly primitives are covered; this is not a claim of a comprehensive assistive-technology certification.
- **Load:** Functional/security tests were executed, not a sustained production load test. The supplied application limiter is local to one API process; add shared gateway limits before running multiple workers.
- **Policy text:** Terms and Privacy pages are supplied as initial product content and should reflect Turacoz’s final operational practices before public launch.

One upstream deprecation warning concerns Starlette’s test client using `httpx`; all tests pass. It does not affect the running application.
