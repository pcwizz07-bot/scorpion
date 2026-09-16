# Scorpion Frontend v1 — Functional UI (design)

Date: 2026-09-16
Status: approved direction (Option 2); implementation pending

## Goal
Give Francois a working web UI for the scorpion FastAPI backend so he can
"see things" (devices, observations, alerts) — deliberately functional, not
pretty. A later pass will make it professional.

## Approach
A self-contained React SPA in `webui/` (Vite + React + Tailwind, its own
package.json) inside this repo, talking only to the scorpion FastAPI REST
API (`/api/v1`). No Convex, no SSR. The old TanStack/Convex root app stays
untouched in the repo for now (removed in a later cleanup pass after v1 is
approved).

### Backend additions (TDD, read-only, auth-guarded)
- `GET /api/v1/observations?limit=&device_id=` — recent observations (auth:
  device token or provisioning token; must return newest-first, masked imsi
  never returned **encrypted only**? no: return imsi_encrypted only if
  requester is provisioning token, else omit sensitive fields — decide:
  v1 returns `imsi_masked` (first 6 + last 2) + mcc/mnc/lac/cell/ts).
- `GET /api/v1/alerts?limit=` — recent alerts (provisioning or device token).
- `GET /api/v1/audit?limit=` — recent audit entries (provisioning token only).
All respect existing auth helpers (`require_device_or_provisioning_token`,
`require_provisioning_token`).

### Frontend (minimal SPA)
- **Auth**: single token input (device or provisioning token) stored in
  `localStorage`; every API call sends `X-Device-Token:<token>`.
- **Pages** (client-side, no SSR data fetch):
  - `Dashboard`: `GET /api/v1/health` + counts (devices, observations,
    alerts via the list endpoints with limit=1 + total? — use limit endpoints
    and show recent lists).
  - `Devices`: table (name, status, last_seen, lat/lng) + register form
    (name/lat/lng → POST register).
  - `Observations`: table of recent observations (imsi_masked, mcc/mnc,
    ts) with refresh.
  - `Alerts`: recent alerts list.
- **Style**: plain Tailwind; dark background; no fancy branding.
- **Deploy**: `vite build` → `dist/` mounted by the FastAPI app (StaticFiles
  at `/` + SPA fallback to index.html for client routes). Single service on
  :8000. Optionally keep dev proxy for local dev.

### Acceptance
- All existing backend tests still green; new read-endpoint tests green.
- `npm run build` succeeds.
- Locally the SPA can list devices/observations/alerts against the live
  backend reachable through ssh tunnel (port 8000) — verified by me.
- Deployed `dist/` served from scorpion-api; `http://<server>:8000` renders,
  API calls work with a pasted token.

### Rollback / risk
- Old `src/` Convex app: keep untouched in git history until v1 approved;
  only replace directory contents after green light. Actually replace at
  implementation time (user wants old UI gone) — old Convex app removed from
  repo; git history preserves it.
- Old dungbeetle web UI on server :3000 purged after new UI verified.
  `/opt/dungbeetle/api-proxy.py` kept unless Francois confirms removal.