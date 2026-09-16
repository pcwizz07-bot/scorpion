# Scorpion — SC-044: Read-only stats portal (Phase C, first slice)

Date: 2026-09-16 · Work ON the Scorpion server (`~/scorpion`, user `bespoke`). Branch `master`.
PUSH IS ALLOWED: commit + push to origin after each area (standing rule).

## Goal
Give Francois a web portal to SEE Scorpion stats (login required). Read-only. POPIA-conscious:
IMSI values are MASKED in the portal; full values remain a later, audited action.

## Scope
### Backend (add to `backend/`, do not change device ingest paths)
1. Config: add `ADMIN_USER`, `ADMIN_PASSWORD`, `TOKEN_SECRET`, `TOKEN_TTL_HOURS` (default 12) to
   `app/config.py` + `.env.example` (placeholders only). Real values are generated on the server.
2. `POST /api/v1/admin/login` — body {username, password}; verify against env (constant-time compare);
   return `{access_token, token_type:"bearer"}`; write an `audit_log` row `admin_login` (actor=username,
   ip=request client). Failed logins: 401 generic, also audited (`admin_login_failed`).
3. JWT dependency `require_admin` (HS256, `TOKEN_SECRET`, `TOKEN_TTL_HOURS`). 401 without/with bad token.
4. `GET /api/v1/admin/stats` (admin) — one JSON object:
   - devices: total, online, list of {name, status, last_seen}
   - observations: total, last_24h, unique_imsis
   - tracked: active count
   - alerts: total, open, by_severity
   - audit the view (`admin_stats_view`).
5. `GET /api/v1/admin/observations?limit=50` (admin) — recent observations with **masked IMSI**
   (show first 6 digits + `****`, never the full value), plus mcc/mnc/country/brand/operator/signal/time/device name.
6. `GET /api/v1/admin/alerts?limit=50` (admin) — recent alerts (type, severity, masked imsi, title, resolved, created_at).
7. Masking helper + tests. NEVER return `imsi_encrypted` or full IMSI anywhere.

### Portal page (no build step — no React, no Convex)
8. Serve a single self-contained page at `GET /portal` (HTML + minimal inline JS/CSS, no external CDNs):
   login form → then stats cards (devices online/total, observations 24h/total, unique IMSIs, tracked, open alerts)
   and two tables (recent observations w/ masked IMSI + device/service, recent alerts).
   Token kept in memory only (no localStorage), auto-refresh every 30 s, logout button.
9. Serve it from the same FastAPI app (`/portal`, static string or `StaticFiles` from a small `backend/app/portal/` dir).

### Deploy (approved)
10. Update the `scorpion-api` user unit on this server to bind `0.0.0.0:8000` (LAN access for the PoC;
    note WireGuard/nginx hardening as later work) and restart. Put `ADMIN_USER`/`ADMIN_PASSWORD`/
    `TOKEN_SECRET` into `~/scorpion/backend/.env` (600) — generate the password/token on the server,
    never in git, and print only "written" + lengths.
11. Verify live: login via curl (200 + token), `/api/v1/admin/stats` with token (200), without token (401),
    `/portal` returns the page (200). Report the exact URL.

## Tests (TDD, run on the server: `cd backend && .venv/bin/python -m pytest -q`)
- login ok/bad (401), stats requires token (401/200), masking format, audit rows written for login + stats view,
  observations endpoint never leaks a full IMSI (assert the raw value is absent from the response body).

## Do NOT
- Touch `pi/`, `convex/`, `frontend/`, `server/` (legacy). Do not weaken device-token auth.
- Do not add non-stdlib frontend tooling. Do not print secrets.
- Report per-area results, test output, the portal URL, and anything you deviated on.