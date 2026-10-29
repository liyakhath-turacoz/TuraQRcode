# TuraQRcode verification

Executed on **29 October 2026** in `E:\TuraQRcode`.

## Results

| Check | Result |
|---|---|
| Application layout | `backend`, `admin`, and `frontend` are independently runnable/buildable application folders. Subsequently consolidated under one root Git repository for the requested GitHub remote, with root README/deployment documentation. |
| Customer production build | Passed: TypeScript and Vite |
| Administrator production build | Passed: TypeScript and Vite |
| Backend/PostgreSQL test suite | 231 tests passed in the full run; the complete-card request boundary and two added social-input regressions also passed: 234 cases total against isolated local PostgreSQL |
| Browser end-to-end suite | 28 scenarios passed in Chromium; public-card checks at 390, 768, and 1280 px |
| Automated accessibility | No violations for the selected WCAG A/AA checks on public, account, workspace, and administrator activity pages |
| QR decoding | Seven module patterns, supported independent corner-frame/center combinations, scan-safe gradient palettes, individually styled labels, frames, and logos decoded with ZXing-C++ |
| Supabase connection | Passed with client-to-Supabase TLS verified through libpq |
| Supabase migrations | Revision `20261029_card_rich_text` applied; eight application tables plus the Alembic version table |
| Supabase data isolation | Private `tura` schema; RLS enabled; Supabase anonymous/authenticated API roles denied schema access |
| Live persistence smoke | Registration, sessions, QR creation/read-back, redirect, scan reporting, downloads, role restriction, and deletion passed |
| Initial administrator | Exists server-side, Argon2id hash verified, administrator role verified, mandatory password change verified |

The live smoke account and its data were removed after testing. The real Supabase administrator’s temporary password was **not changed by tests**. Administrator password changes in browser tests occur only in the local `tura_e2e` database.

## Feature coverage

| Feature | Evidence |
|---|---|
| Registration and required policies | API rejects either missing consent; browser requires checkbox; timestamp and policy version persist |
| Sign-in/logout and profile | Correct/incorrect credentials, case normalization, session expiry, logout revocation, browser profile read-back |
| Password change and recovery | First-admin-login restriction, strong password validation, other-session revocation, invalid/expired/reused tokens, administrator-assisted browser recovery |
| Authorization | Member-to-admin rejection; cross-user read/edit/delete/download/export/analytics denial; role injection rejected |
| URL shortening and aliases | Custom slug resolution, collision rejection, short-link mode, immutable QR redirect address after destination updates |
| QR content | Website, exact plain text, email, telephone, SMS, Wi-Fi escaping/whitespace, UPI, form/app/file URLs, validated social destinations, WhatsApp links, UTF-8 SSID length, and vCard; supported URL-based types can be dynamic and editable |
| QR appearance | Colors/contrast, square/rounded/dot patterns, raster logo validation/normalization, frame; actual PNG decoding |
| Export formats | PNG, SVG, PDF signatures, browser downloads, ZIP content, A4 print PDF |
| Link controls | Pause/reactivate, expiry, password form/retry/unlock/removal; actual Chromium form navigation to another origin for signed-in desktop and anonymous mobile visitors; 303 GET redirect; disconnected-body handling |
| Analytics | Distinct scan/click channels, counts, UTC daily aggregates, device categories, referrer-host redaction, CSV, top codes |
| Saved-code organization | Search, filters, pagination, alphabetical sort, deletion, default assignment and safe reassignment on project removal |
| Barcodes | All five standards saved/exported and decoded; EAN/UPC check digits; invalid standards/values rejected; separate barcode history, appearance controls, tracked Code 128 redirects, barcode scan analytics, and static-value protection covered in API and browser tests |
| Default projects | Registration and migration create defaults, create/bulk/edit assign automatically, default deletion blocked, custom deletion reassigns |
| Business cards | Any brand color with readable public profile and decodable QR; create/edit/delete, escaped public HTML, public profile, vCard, downloadable QR; browser flow verified |
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

## Blue design and generator expansion

The existing migration/backfill verification remains valid. Code types and QR appearance remain in existing JSON records. Business-card profile/theme/media migrations add the fields for images, experience, social links, and professional sections; the current schema head is `20261029_card_rich_text`. A read-only Supabase check this run confirmed connection/TLS and the current application schema revision. The prior migration/backfill verification established: before/after counts for users, codes, and business cards matched; every existing account has a default project and no code remains unassigned. Existing custom project assignments and the real administrator password/state were preserved. The live smoke script verifies current Alembic head, default-project protection, protected unlock, barcode storage/exports, ordinary CRUD/analytics, and removes only its temporary account.

The 28 browser scenarios include public/account/workspace accessibility checks, coordinated QR color presets, blocked low-contrast custom pairs, module and corner-marker shape controls, independently styled movable QR labels, gradient palette and editor controls for expiry/alias/password/mobile destination, frame choices, mobile design layout, EAN check-digit validation, barcode exports/saving, tracked Code 128 scan history and appearance, QR type selection and dynamic form links, custom short links, bulk-import row errors, and desktop/mobile password navigation. QR image tests also decode gradient exports, labels, and supported marker combinations with ZXing-C++.

Firecrawl captured both reference pages and screenshots. Chrome DevTools MCP captured QRStuff and the updated local pages; its Bitly navigation timed out, with Firecrawl providing that page evidence. Reference capture files and tools remain ignored under `backend/.local`. No reference-site login was required for the public-page review. See the design-system reference review for feature scope.

The running development setup was also checked at customer port 5173, administrator port 5174, and API port 8000 with the project virtual environment: QR preview, barcode preview, Supabase readiness, and the administrator sign-in screen passed with no browser JavaScript exceptions. The combined launcher now re-executes inside the project venv when available, preventing accidental use of missing global Python dependencies.

## Square export and professional profile verification

- PNG/SVG files with labels, borders and logos have exact square dimensions at 256, 354, 1,024, 1,080, 1,200, 2,480 and 3,000 px. PNGs report 300 DPI. PDF MediaBox dimensions vary with the selected size; only the explicit A4 option adds a rectangular paper sheet.
- All 100 original palette combinations and all 96 new featured linear/radial multicolor combinations decode with ZXing-C++; classic and inverted designs are also covered. Browser tests confirm the 198-option picker starts with the two classics and then the featured gradients.
- Labels at zero sit at the outer clear-margin boundary; maximum positions reach the square canvas edge. The four-module scan margin stays clear. Raster and SVG use one vector composition, including proportional logo placement.
- Barcode tests cover all five standards, check digits, long tracked destinations, saved/unsaved appearance, exact requested width where the standard permits it, caption units, and PNG/SVG/PDF. The actual running local API was checked after replacing the unrelated `barcode` package with `python-barcode==0.16.1`; both QR and barcode PNGs decoded.
- Browser tests verify nested-editor scroll chaining, separate `/app/barcodes/:id` navigation, and completed record creation rather than matching `/new` during a pending save.
- Card media tests create, reload, edit/remove profile photos, covers, and company logos. Structured experience and ten supported social platforms persist and render on the public profile. Public mobile rendering and automated accessibility pass. Light brand accents retain a decorative role in the hero while white panels use a readable link color.
- Deleting a card's QR from Overview removes the card, public profile, linked QR and activity consistently. Valid bulk rows keep their default project, invalid/duplicate rows report failures, ZIP images decode as square QR artwork, and empty/oversized batches are rejected.
- A fresh Supabase smoke account verified image/experience/social persistence, linked deletion, long tracked barcode export, existing QR/auth/analytics flows, migration head, TLS, and access restrictions. Its data was removed in the cleanup block; existing administrator credentials/state were preserved.

Physical camera/printer testing, sustained production load, and deployment-specific SMTP delivery are outside these automated results.

## Inline profile editor and export follow-up

- Bio, experience descriptions, and custom sections now use an inline Tiptap toolbar. The browser test exercises every formatting action, including nested list indentation, undo/redo, and clearing formatting, then saves, reopens, and checks the published HTML. Automatic trailing paragraphs were disabled to prevent empty list items when switching list styles.
- `nh3` sanitizes saved and published rich text with a strict tag allowlist and no attributes. Script, style, SVG, iframe, event-handler, and unsafe-link inputs are removed. Plain text remains separately available. Existing plain-text records render as escaped text.
- Profile photos and covers have validated minimums and fixed output canvases; logos preserve their proportions. Browser tests upload all three slots, adjust crops, save/reopen, and remove media. Backend tests cover too-small dimensions, oversized images, malformed data, and all three output sizes. A complete card request over 2 MB saves successfully within the dedicated 3 MB card limit; oversized card and ordinary API bodies are rejected.
- The published profile uses a continuous header, professional timeline, contact column, and responsive sections. Desktop and mobile screenshots were reviewed. Tests check full-width covers, no horizontal overflow, vCard downloads, and selected WCAG A/AA rules at 390, 768, and 1280 px.
- Social fields normalize handles and URLs before saving. YouTube channel IDs and legacy paths, LinkedIn company paths, international-safe URL quoting, supported card social platforms, unsafe-host rejection, and invalid display-name inputs are covered. QR previews, saved destinations, destination edits, and redirects use the normalized address.
- All 16 QR content types were exported at 354 px with a logo and labels. PNGs decode directly, SVGs decode after rendering, and PDF-embedded images are extracted with pypdf and decoded with ZXing-C++. Seven module patterns × four frames × three small/standard sizes also decode with logos and labels (84 combinations). Square modules now use crisp-edge rendering at native export resolution.
- The actual five-row CSV in `frontend/public/examples/bulk-5.csv` is tested through the API for editable/static QR and short-link modes, default project assignment, redirects, and decodable ZIP images. The browser downloads that same file, creates five short links, verifies separate Links/QR histories, and checks invalid-row feedback.
- Both application production builds passed. The business-card editor is loaded separately from the public generator; the main JavaScript bundle is about 450 KB before compression. The live Supabase smoke test verifies rich text, normalized social handles, image persistence, migration head, protected redirects, analytics, exports, and cleanup of its temporary account. The actual running API at port 8000 returned readiness 200 and generated decodable 1,200 px QR/barcode PNGs.

Image-layout research used [HiHello's official image guidance](https://support.hihello.com/hc/en-us/articles/14639880824475-What-format-size-and-resolution-should-I-use-for-pictures-and-videos) and [Blinq's image layout guidance](https://support.blinq.me/en/articles/68009-changing-your-card-image-layout); TuraQRcode's limits are product-specific. Channel input handling follows [YouTube's URL guidance](https://support.google.com/youtube/answer/6180214).
