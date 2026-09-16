# Scorpion — SC-044: Frontend v1 implementation (per the APPROVED design)

Date: 2026-09-16 · Work ON the Scorpion server (`~/scorpion`, user `bespoke`), branch `master`.
PUSH IS ALLOWED after each area (standing rule).

**This implements the already-approved `docs/superpowers/specs/2026-09-16-frontend-v1-design.md`
("Option 2", functional-not-pretty). Read that file first; where this file and it disagree, it wins.
Ignore the earlier single-file-portal sketch — superseded.**

## Backend (TDD, read-only, auth-guarded — reuse existing helpers)
1. `GET /api/v1/stats` — auth: device or provisioning token. Returns counts for the dashboard cards:
   devices total/online, observations total + last 24 h, unique IMSIs, tracked active, alerts total/open.
2. `GET /api/v1/observations?limit=&device_id=` — newest-first; existing auth helper; returns
   `imsi_masked` (first 6 + last 2 digits, e.g. `123456****45`), mcc, mnc, lac, cell_id, country, brand,
   operator, signal_dbm, observed_at, device name. NEVER the full or encrypted IMSI.
3. `GET /api/v1/alerts?limit=` — recent alerts (type, severity, masked imsi if any, title, message,
   resolved, created_at).
4. `GET /api/v1/audit?limit=` — recent audit rows; **provisioning token only** (device token → 403).
5. Masking helper + tests proving no full IMSI leaks in any response body.
6. Do not change the device ingest endpoints or weaken device-token auth.

## Frontend (`webui/` — self-contained SPA, no Convex, no SSR)
7. Vite + React + Tailwind, its own `package.json` (node/npm exist on this server — the retired dashboard used them).
   Dev proxy to `http://127.0.0.1:8000`; production build served as static files.
8. Auth: single token input (device or provisioning token), kept in `localStorage`, sent as
   `X-Device-Token: <token>` on every call; "Sign out" clears it.
9. Pages (client-side routing fine): **Dashboard** (health + stat cards from `/api/v1/stats`),
   **Devices** (table: name, status, last_seen, lat/lng + register form → POST /api/v1/devices/register
   using the provisioning token), **Observations** (table with masked IMSI, refresh), **Alerts** (recent list).
10. Keep it functional and readable; no external CDNs; errors shown plainly (401 → "token rejected").

## Deploy (approved)
11. Build `webui/dist` and serve it: simplest reliable path = FastAPI `StaticFiles` mount at `/portal`
    (same app, same origin, no CORS) — document the choice. Keep `scorpion-api` bound to `0.0.0.0:8000`
    for the LAN PoC (WireGuard/nginx hardening is later work).
12. Restart the service and verify live: `/portal` returns the SPA (200), `/api/v1/stats` with a valid
    token (200) and without (401), and a browser-less check that the built JS bundle is referenced.
    Report the exact URL to open.

## Tests / verification (run on the server: `cd backend && .venv/bin/python -m pytest -q`)
- New endpoint tests (auth matrix: no token 401, device token 200 on stats/observations/alerts,
  device token 403 on audit, provisioning token 200 on audit) + masking assertions + no-leak assertion.
- Full existing suite must stay green (68 → 60+ backend tests, whatever the count — report it).
- Report per-area results, test output, portal URL, and every deviation/decision.

## Do NOT
Touch `pi/`, `convex/`, legacy `frontend/`, legacy `server/`. Do not print secrets. Do not add analytics/CDNs.