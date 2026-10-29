# TuraQRcode

**TuraQRcode by Turacoz** is a QR-code, barcode, and short-link platform for creating, customizing, organizing, sharing, and measuring connections. QRStuff and Bitly are feature references; this application has its own interface and branding.

The repository contains three applications that can be installed, run, and built independently:

| Application | Technology | Local URL |
|---|---|---|
| `frontend` | React, TypeScript, Vite | http://127.0.0.1:5173 |
| `admin` | React, TypeScript, Vite | http://127.0.0.1:5174 |
| `backend` | Python FastAPI, SQLAlchemy, Alembic | http://127.0.0.1:8000 |
| Database | Supabase PostgreSQL | Server-side connection; not a browser application |

[CloudPanel deployment and update guide](DEPLOYMENT.md) · [Verification report](backend/docs/VERIFICATION.md) · [Product plan](frontend/design-system/turaqrcode/TuraQRCode_Project_Reference.md)

## Requirements

- Node.js 22 and npm. The local development build was verified on Node.js 22.11.
- Python 3.13, the tested Python runtime.
- A Supabase PostgreSQL connection string, or an appropriate PostgreSQL database owned by the server role.
- Git. Docker is optional; the normal local and CloudPanel workflows do not require it.

## Clone the repository

```powershell
git clone https://github.com/liyakhath-turacoz/TuraQRcode.git
cd TuraQRcode
```

The commands below assume a Windows checkout at `E:\TuraQRcode`. Use your actual clone path. Linux production commands are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Run the applications individually

Run the backend first, then start each React app in a separate terminal. There is no root npm workspace or root dependency installation.

### 1. Backend — first setup

```powershell
cd E:\TuraQRcode\backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Edit `backend/.env` locally. Set `DATABASE_URL` to the Supabase PostgreSQL URI from **Connect → Session pooler**, not the HTTPS project URL. URL-encode special characters in the database password. Set `INITIAL_ADMIN_EMAIL` and a temporary `INITIAL_ADMIN_PASSWORD` if you are initializing a new database. Keep real values out of Git.

```powershell
.venv\Scripts\python.exe -m app.manage check
.venv\Scripts\python.exe -m app.manage init
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Readiness: http://127.0.0.1:8000/api/ready. API documentation: http://127.0.0.1:8000/api/docs.

For later starts, run only the Uvicorn command. Run `app.manage migrate` when schema changes require a migration. `app.manage init` is idempotent for an existing administrator and does not change its password.

### 2. Customer frontend — separate terminal

```powershell
cd E:\TuraQRcode\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. On later starts, run `npm run dev`; rerun `npm ci` when the dependency lockfile changes or when installing a fresh checkout.

### 3. Administrator frontend — separate terminal

```powershell
cd E:\TuraQRcode\admin
npm ci
npm run dev
```

Open http://127.0.0.1:5174. The backend creates administrators; browser registration cannot grant an administrator role. The initial administrator must replace its temporary password before using protected operations. Bootstrap passwords belong only in the server environment, never a frontend file.

### Optional: start all three together

After completing dependency installation and backend initialization:

```powershell
cd E:\TuraQRcode\backend
.venv\Scripts\python.exe scripts\dev.py
```

This starts the backend, customer app, and administrator app. The launcher uses the project virtual environment when it exists, even if invoked through a global Python interpreter. Ctrl+C stops them. The local PostgreSQL helper is not needed when using Supabase normally.

## Complete project structure

Generated or private paths are marked **local only**; they are deliberately absent from a fresh clone.

```text
TuraQRcode/
├── README.md                         Product, setup, pages, and feature inventory
├── DEPLOYMENT.md                     CloudPanel deployment, updates, rollback, and secrets
├── .gitignore                       Excludes dependencies, secrets, and generated output
├── .gitattributes                   Consistent text/Unix deployment file endings
├── backend/
│   ├── README.md
│   ├── .env.example                 Safe server configuration template
│   ├── .env                         LOCAL ONLY: real database/SMTP/bootstrap configuration
│   ├── .venv/                       LOCAL ONLY: Python dependencies
│   ├── .local/                      LOCAL ONLY: test PostgreSQL files and local backups
│   ├── requirements.txt             Production Python dependencies
│   ├── requirements-dev.txt         Test and audit dependencies
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                  FastAPI setup, request protection, errors, health
│   │   ├── config.py                Environment loading
│   │   ├── db.py                    PostgreSQL engine, sessions, TLS
│   │   ├── models.py                Application data models
│   │   ├── schemas.py               Input and QR-content validation
│   │   ├── security.py              Password hashing, sessions, roles, rate limits
│   │   ├── qr.py                    QR payloads, raster/vector/PDF rendering
│   │   ├── routes_auth.py           Registration, login, profile, password/recovery
│   │   ├── routes_codes.py          Codes, redirects, analytics, projects, bulk/exports
│   │   ├── routes_cards.py          Business cards and public contact pages
│   │   ├── routes_admin.py          Administrator operations and audit history
│   │   └── manage.py                Check, migrate, initialize, Supabase checks
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/                Versioned database migrations
│   ├── scripts/
│   │   ├── dev.py                   Optional combined local launcher
│   │   ├── local-db.mjs             Isolated local PostgreSQL helper
│   │   ├── serve-e2e.py             Guarded browser-test API launcher (Windows)
│   │   └── supabase-smoke.py         Temporary-account live persistence checks
│   ├── tests/                       PostgreSQL/API/security/QR decoding tests
│   ├── tools/
│   │   ├── package.json             Optional local PostgreSQL tooling
│   │   └── package-lock.json
│   ├── docs/VERIFICATION.md
│   ├── deploy/cloudpanel/           Nginx routing fragments and systemd service example
│   ├── Dockerfile                   Optional container backend
│   ├── .dockerignore
│   └── compose.yml                  Optional three-application container stack
├── frontend/
│   ├── README.md
│   ├── .env.example                 Optional public API-origin setting
│   ├── package.json
│   ├── package-lock.json
│   ├── index.html
│   ├── vite.config.ts               Development API/redirect/card proxy
│   ├── tsconfig.json
│   ├── public/favicon.svg
│   ├── src/
│   │   ├── main.tsx                 Customer routes and application startup
│   │   ├── styles.css
│   │   ├── accessibility.css
│   │   ├── shared/                  This app's API, account, UI, type/style primitives
│   │   ├── components/              Layout, QR/barcode builders, safe colors, link previews, charts
│   │   └── pages/                   Public/legal, codes, organization, bulk, settings
│   ├── design-system/turaqrcode/     Visual guidance and product reference plan
│   ├── playwright.config.ts
│   ├── tests/e2e/product.spec.ts     Complete customer/administrator browser scenarios
│   ├── tests/screenshots/           Representative verified interface screenshots
│   ├── Dockerfile
│   ├── nginx.conf                   Optional container Nginx configuration
│   ├── .dockerignore
│   ├── node_modules/                LOCAL ONLY: recreated with npm ci
│   └── dist/                        LOCAL ONLY: recreated with npm run build
└── admin/
    ├── README.md
    ├── .env.example
    ├── package.json
    ├── package-lock.json
    ├── index.html
    ├── vite.config.ts               Development API proxy
    ├── tsconfig.json
    ├── public/favicon.svg
    ├── src/
    │   ├── main.tsx                 Admin routes, layout, accounts, moderation, audit
    │   ├── shared/                  This app's own account/API/UI primitives
    │   ├── styles.css
    │   └── accessibility.css
    ├── Dockerfile
    ├── nginx.conf                   Optional container Nginx configuration
    ├── .dockerignore
    ├── node_modules/                LOCAL ONLY
    └── dist/                        LOCAL ONLY
```

The customer and administrator apps keep their own UI primitives so each builds without importing source from the other application. Git history is managed at the repository root; these folders are not Git submodules.

## Exact implemented features

| Area | Implemented behavior |
|---|---|
| Public generator | Account-free static QR preview and PNG/SVG/PDF downloads |
| QR content types | Website URL, plain text, email, telephone, SMS, Wi-Fi, UPI payment, form URL, app listing, public file URL, WhatsApp, YouTube, Instagram, Facebook, LinkedIn, and vCard contact details. Form and file codes point to an existing public URL; TuraQRcode does not host the file or create the form. |
| QR modes | Static QR codes for all supported content types; editable, trackable website, form, app, file, and supported social URL QR codes plus short links; trackable Code 128 barcodes that open a website; fixed-value retail and inventory barcodes |
| Design | Seven module patterns, independent corner-frame and center styles, 20 contrast-checked solid and gradient palettes, optional foreground/marker colors, independently styled labels that can be moved above or below the code, callout/border frames, and raster PNG/JPG/WebP logo up to 500 KB and 4 megapixels |
| Barcodes | Separate saved barcode history; Code 128, Code 39, EAN-13, EAN-8, UPC-A; EAN/UPC check digits; optional value caption; high-contrast color presets and custom colors; adjustable bar width, height, and caption size; PNG/SVG/PDF and saved bundle/print exports. Track scan requests with managed Code 128 website links. |
| Exports | PNG (256–2048 px through saved-code API), SVG, PDF, ZIP bundle with CSV index, and nine-code A4 print sheets |
| Short links | The Links workspace lists short links only; it has its own create flow, destination, generated/custom alias, search, status/project filters, sorting, pagination, pause/resume, expiry, password protection, mobile destination, and click history. Aliases are 3–64 letters, numbers, hyphens, or underscores and globally unique |
| Editable destinations | Update a managed URL without changing its short address or QR payload |
| Link controls | Pause/reactivate, optional expiry, optional access password, optional alternate mobile destination |
| Saved codes | QR, Links, and Barcodes each have separate saved lists. The QR list excludes short links and barcodes; the Links list includes short links only; Barcode history contains barcode records only. Search, relevant filters, project selection, sort, pagination, edit, delete, and export are available |
| Overview | Code/active-code counts, clicks/scans, 14-day activity, top connections, devices, recent codes, quick-create shortcuts |
| Analytics | Each trackable redirect is saved against its code with time, link-click or QR-scan channel, device category, and referrer host. Per-link activity is opened from its click count; reporting includes date filters, UTC daily trends, latest 25 requests, and CSV export up to 50,000 rows |
| Projects | Every account receives a default project; new codes, links, barcodes, and bulk rows go there unless another project is selected. Project cards link to separate QR, Links, and Barcodes lists. Existing unassigned codes are migrated. Rename/color projects; deletion moves items to the default project, which cannot be deleted |
| Business cards | Name, title, company, email, phone, one website/social-profile URL, any custom card color with automatic readable text and a contrasting exported QR; create/edit/delete, public profile, vCard download, QR export, copy address |
| Bulk UI | CSV upload or paste, column mapping, URL or text batches, editable/static/short-link selection as applicable, row-level results, ZIP/print export; maximum 100 rows and 100 KB CSV input |
| Bulk API | Up to 100 supported code objects per request; validation and alias conflicts reported per row while valid rows are saved |
| Registration | Name/email/password; required combined Terms & Conditions and Privacy Policy checkbox; consent timestamp and policy version recorded |
| Accounts | Login, logout, profile-name changes, password change, session expiry/revocation, recovery request, single-use expiring reset links |
| Administrator | Platform counts, account/code search and pagination, account suspension/restoration, code pause/activation, confidential recovery links, account/admin audit history |
| Administrator protection | Server-only bootstrap, Argon2id password hashes, mandatory initial password change, backend role checks; administrator accounts cannot be suspended from the panel |
| Data protection | Owner access checks, private PostgreSQL schema/RLS, HttpOnly SameSite session cookies, Origin checks, request/content/logo validation, single-process rate limits, TLS for remote PostgreSQL |
| Deployment configuration | One stable branded link hostname via PUBLIC_BASE_URL; optional SMTP recovery email |

### Important behavior and limits

- Static QR content and direct retail barcode values are fixed. Static scans are not tracked; pausing or deleting a saved static record cannot disable an already downloaded code. Choose an editable website, form, app, file, or supported social URL QR code—or tracked Code 128 barcode—to measure scans.
- Editable codes and short links depend on the running service, active account/link, and public hostname. Set that hostname before distributing codes; changing configuration cannot rewrite printed images.
- A short link’s current destination and settings are saved in PostgreSQL. Its visit events are retained as activity history and removed with the link. Editing a destination replaces the current destination; prior destination revisions are not retained.
- Analytics count requests, including repeats and bots. They do not claim unique people, precise geolocation, or verified human scans. Referrers/devices can be incomplete.
- Profile email changes and self-service account deletion are not implemented. Account recovery is available through SMTP when configured or through the administrator-assisted workflow.
- There is no billing/subscription UI, file/media QR hosting, GS1, integration marketplace, per-account custom-domain provisioning, or multi-social-link business-card editor in this release.
- SMTP delivery and public domain/HTTPS hosting require deployment-specific credentials/configuration. Functional tests are not a production load test.

## Complete page inventory

### Customer app — 23 routes

| Route | Page | Access |
|---|---|---|
| `/` | Product home and public static QR generator | Public |
| `/barcode-generator` | Public barcode generator and exports | Public |
| `/login` | Sign in | Public/account access |
| `/register` | Sign up and required legal acceptance | Public/account access |
| `/forgot-password` | Recovery instructions | Public/account access |
| `/reset-password?token=...` | Set password with a valid recovery token | Token holder |
| `/terms` | Terms & Conditions | Public |
| `/privacy` | Privacy Policy | Public |
| `/change-password` | Initial/explicit password change | Signed-in account |
| `/app` | Overview/dashboard | Signed-in account with password requirement satisfied |
| `/app/codes` | Saved QR codes | Signed-in owner |
| `/app/create` | Create QR code/short link | Signed-in account |
| `/app/links` | Short links only, with click-count links to per-link activity | Signed-in owner |
| `/app/links/new` | Short-link creator, UTM tags, link controls | Signed-in account |
| `/app/links/:id` | Short-link details, destination editor, and activity | Owner |
| `/app/barcodes` | Saved barcodes | Signed-in owner |
| `/app/barcodes/new` | Barcode creator | Signed-in account |
| `/app/codes/:id` | Code details and editor | Owner |
| `/app/analytics` | Analytics and CSV reporting | Signed-in owner |
| `/app/projects` | Projects/campaigns | Signed-in owner |
| `/app/business-cards` | Digital business cards | Signed-in owner |
| `/app/bulk` | Bulk create and print | Signed-in account |
| `/app/settings` | Profile and password/security | Signed-in account |

Secondary actions use dialogs rather than additional pages. Unknown routes show a friendly missing-page screen.

### Administrator app — 6 routes on its own origin

| Route | Page |
|---|---|
| `/login` | Administrator sign in |
| `/change-password` | Replace temporary/change current password |
| `/` | Platform overview |
| `/users` | Accounts, suspension/restoration, recovery assistance |
| `/codes` | Cross-account code/link moderation |
| `/audit` | Account and administration activity log |

Except sign-in, administrator routes require an authorized administrator; normal operations are blocked until the initial password is replaced.

### Public visitor paths served by FastAPI

| Path | Behavior |
|---|---|
| `/r/{slug}` | Managed redirect, or password form when protected |
| `/c/{slug}` | Published digital business-card profile |
| `/c/{slug}/contact.vcf` | Download published contact details |

API documentation is at `/api/docs`; liveness is `/api/health`; database/application readiness is `/api/ready`.

## Build commands

```powershell
cd E:\TuraQRcode\frontend
npm ci
npm run build

cd E:\TuraQRcode\admin
npm ci
npm run build
```

Each app creates its own `dist`. Production serves these files with Nginx and routes API/redirect/card requests to FastAPI. Vite's development server and `scripts/dev.py` are local development tools, not production services.

## Tests and verification

The current verification covers **129 backend tests, 19 Chromium browser scenarios, successful builds for both React applications, and no known vulnerabilities in the dependency audits**. Live Supabase checks covered TLS, migrations, administrator state, temporary-account CRUD, default projects, protected unlocks, barcode exports, redirects, analytics, downloads, authorization, and cleanup. See [the verification report](backend/docs/VERIFICATION.md) for exact coverage and limits.

To reproduce tests on the Windows development environment, first start genuine isolated local PostgreSQL in a separate terminal:

```powershell
cd E:\TuraQRcode\backend\tools
npm ci
npm run db:local
```

Then:

```powershell
# Backend/API/QR decoding tests — dedicated local tura_test database only
cd E:\TuraQRcode\backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip_audit --progress-spinner off

# Browser suite starts its own servers and a separate local tura_e2e database
cd E:\TuraQRcode\frontend
npx playwright install chromium
npm run test:e2e
```

Destructive test launchers guard the loopback hostname and dedicated database names; do not point them at production. Browser tests use 8011/5183/5184. SMTP delivery, Docker/CloudPanel deployment, and production load were not verified without the relevant deployment environment.

## What goes to GitHub

Commit source, package manifests, `package-lock.json` files, Python requirement files, migrations, tests, documentation, and safe `.env.example` templates. Do not commit actual `.env` files, database/SMTP/bootstrap credentials, `node_modules`, `.venv`, `.local`, `dist`, database backups, or test reports.

After cloning or updating a server, recreate dependencies with `npm ci` and `python -m pip install -r requirements.txt`, create the private server `.env`, apply migrations, build both frontends, and restart the API. [DEPLOYMENT.md](DEPLOYMENT.md) explains exactly which values/files change, which services restart, how to publish new static builds, and how to preserve secrets during updates.

## Blue design and generator update ? 29 October 2026

The browser suite exercises actual protected-form navigation to a different origin for desktop and mobile visitors, including wrong-password retry. Interrupted form requests are handled without an unhandled `ClientDisconnect`; successful unlocks use an HTTP 303 destination GET. The public password page permits HTTP(S) redirect destinations in its form policy while retaining other page restrictions.

The Supabase migration `20261029_default_projects` was applied and verified against existing record counts. It preserves custom project assignments, creates a default for existing users, and assigns previously ungrouped codes. New deployments run the usual migration command; no additional environment keys or research-service credentials are needed.

Reference research and feature decisions: [reference review](frontend/design-system/turaqrcode/REFERENCE_REVIEW.md). Firecrawl/Chrome capture files and local research tooling remain ignored under `backend/.local`; they are not product runtime dependencies.
