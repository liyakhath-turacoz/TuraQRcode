# TuraQRcode · Customer application

React + TypeScript + Vite. This independent application is the customer-facing product for TuraQRcode by Turacoz. It follows [the project plan](design-system/turaqrcode/TuraQRCode_Project_Reference.md) with its own visual identity.

[Complete structure, exact features, and pages](../README.md) · [CloudPanel deployment and updates](../DEPLOYMENT.md)

```powershell
cd E:\TuraQRcode\frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Run FastAPI on port 8000 using `../backend/README.md`. Vite proxies API requests and public link/card routes to that server. The public generator works without an account; saving and editable links require sign-in.

For later starts, `cd E:\TuraQRcode\frontend` and `npm run dev`. Run `npm ci` again when installing a fresh checkout or when `package-lock.json` changes. There is no root npm install. Keep the backend and administrator app in their own terminals.

```powershell
npm run build
```

This checks TypeScript and produces `dist`. Serve it with an SPA fallback and proxy `/api`, `/r`, and `/c`. The included Nginx configuration handles those routes. `VITE_API_URL` is optional when using an API on a different origin; configure cookies, HTTPS, and allowed origins accordingly. Never put database passwords, bootstrap credentials, or private keys in a `VITE_` variable.

## Pages

Public: `/`, `/barcode-generator`, `/login`, `/register`, `/forgot-password`, `/reset-password`, `/terms`, `/privacy`.

Workspace: `/app`, `/app/codes` (QR codes only), `/app/create`, `/app/links` (short links only), `/app/links/new`, `/app/barcodes`, `/app/barcodes/new`, `/app/codes/:id`, `/app/analytics`, `/app/projects`, `/app/business-cards`, `/app/bulk`, `/app/settings`. Link click counts open their filtered activity history. Temporary-password accounts go to `/change-password` before entering their workspace.

QR Scanner is at `/app/scanner`, last in Manage below Bulk & print. It reads QR codes and supported barcodes from a camera or PNG/JPG/WebP image, displays/copies contents, and opens web links. Automatic navigation is optional and off by default. The camera requires permission and HTTPS (or localhost), and stops when scanning completes, the page is hidden, or the user stops/leaves. Files stay on the device; scanning creates no saved-code or history records. Image limits are 12 MB, 8,000 px per side, and 24 megapixels. The decoder and scanner styles load only when visiting this page.

## Browser tests

Start the isolated PostgreSQL helper from `backend/tools` first. Then:

```powershell
npx playwright install chromium
npm run test:e2e
```

Playwright starts a test API on 8011 and React servers on 5183/5184. Those ports must be free. It uses a guarded local `tura_e2e` database, not Supabase. Tests cover generation/downloads, required legal acceptance, sign-in protection, code CRUD and tracking, projects, cards, bulk processing, print exports, profile/password changes, administrator access and recovery, mobile overflow/navigation, and automated WCAG checks. HTML reports are written to `playwright-report`; screenshots are in `tests/screenshots`.

Run scanner checks alone with `npx playwright test tests/e2e/scanner.spec.ts`. They exercise actual image and virtual-camera decoding, all five generated barcode standards, inverted QR, safe/automatic link handling, invalid files, permission errors, pending-request cancellation, camera selection and cleanup, keyboard controls, mobile overflow, and accessibility. Virtual camera tests do not establish physical-device compatibility.

`src/shared` contains this app’s own account and design primitives; the administration app keeps its own copy so both folders build independently. There are no workspace-root dependencies.
