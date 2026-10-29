# TuraQRcode · Administration

Independent React + TypeScript + Vite administration application for Turacoz.

[Complete structure, exact features, and pages](../README.md) · [CloudPanel deployment and updates](../DEPLOYMENT.md)

```powershell
cd E:\TuraQRcode\admin
npm ci
npm run dev
```

Open **http://127.0.0.1:5174**. Run the FastAPI service on port 8000 first. Sign in with the administrator initialized on the server. The initial email is `Admin@turacoz.com`; the temporary password is configured privately in the backend environment. A password change is required before any administrative operation. No account is seeded by browser code, and ordinary members cannot enter administration.

For later starts, `cd E:\TuraQRcode\admin` and `npm run dev`. Run `npm ci` for fresh dependencies or a changed lockfile. This app does not share `node_modules` with the customer frontend.

Routes: `/login`, `/change-password`, `/` (overview), `/users` (account management/recovery), `/codes` (moderation), and `/audit` (activity history). These belong to the administrator app's origin, separately from customer routes with similar names.

Capabilities: platform summary, account search and suspension/restoration, confidential one-time account-recovery links, saved-code moderation, and audit history. Administrator accounts cannot be suspended through this interface. Recovery links require identity verification before an administrator shares them with the account holder.

```powershell
npm run build
```

Production output is `dist`. Serve with an SPA fallback and proxy `/api` to FastAPI. See `../backend/README.md` for HTTPS, cookie, CORS, database, and deployment settings. Never place a database connection string or private key in a frontend environment variable. The customer application’s Playwright suite exercises this separate admin app as part of the complete product.
