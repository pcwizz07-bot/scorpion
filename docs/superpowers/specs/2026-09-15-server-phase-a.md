# Scorpion — Phase A: Server Backend (FastAPI + PostgreSQL)

Date: 2026-09-15 · Status: **IMPLEMENTED + VERIFIED 2026-09-15** — branch `phase-a-server-backend` (7 commits); 17 pytest tests pass; live curl e2e (register/heartbeat/observation/dedup/401) verified; pushed to GitHub.
IGNORE the root CLAUDE.md — its Convex guidance does NOT apply to the new `backend/` (FastAPI).

## Context
Port the Scorpion server side OFF Convex (cloud) to self-hosted FastAPI + PostgreSQL.
The Convex code in `convex/` is the REFERENCE for business rules — READ it, do NOT modify it.
Old proxies `server/api-proxy.py` + `server/api-server.mjs` are replaced by this backend (delete later, NOT now).

## Stack (locked)
- Python 3.12, uv project inside `backend/`
- FastAPI, Pydantic v2, SQLAlchemy 2 (declarative, sync engine), Alembic
- PostgreSQL 16 — dev container already provisioned:
  `postgres://scorpion:REDACTED_DEV_PASSWORD@127.0.0.1:5432/scorpion`
- `cryptography` (Fernet) for IMSI-at-rest encryption
- pytest + httpx TestClient — **TDD: write failing tests first per feature**

## Layout (create under backend/)
```
backend/
  pyproject.toml, uv.lock
  .env.example          (committed, placeholder values only)
  .env                  (local dev values, NEVER committed — root .gitignore already ignores `.env`)
  .gitignore            (backend: .env, __pycache__/, .venv/, .pytest_cache/)
  alembic.ini
  alembic/ (env.py, versions/0001_init.py)
  app/
    __init__.py
    main.py             (FastAPI app factory, /api/v1/health, lifespan)
    config.py           (pydantic-settings from env: DATABASE_URL, PROVISIONING_TOKEN, CRYPTO_KEY, DEDUP_WINDOW_SECONDS=60)
    db.py               (engine, SessionLocal, Base, get_db dependency)
    models.py           (SQLAlchemy models)
    schemas.py          (Pydantic models)
    crypto.py           (imsi_encrypt / imsi_decrypt / imsi_hash)
    security.py         (provisioning-token check, device-token check)
    audit.py            (write audit row helper)
    api/__init__.py
    api/devices.py
    api/observations.py
    cli.py              (retention purge command, dry-run default)
  tests/
    conftest.py
    test_crypto.py
    test_auth.py
    test_devices.py
    test_observations.py
    test_retention.py
```

## Schema (PostgreSQL — Alembic migration 0001)
- `devices`: id UUID pk (gen_random_uuid), name text unique not null, lat/lng double precision not null,
  altitude double precision null, status text not null default 'online', last_seen timestamptz not null,
  firmware_version text null, device_token_hash text not null unique (sha256 hex of returned token),
  created_at timestamptz default now()
- `imsi_observations`: id bigserial pk, device_id UUID fk devices not null, imsi_encrypted bytea not null,
  imsi_hash text not null (sha256(imsi+pepper) hex), mcc/mnc text null, lac/cell_id int null,
  country/brand/operator text null, signal_dbm/snr_db int null, arfcn int null, frequency double precision null,
  tmsi1/tmsi2 text null, observed_at timestamptz not null, created_at timestamptz default now()
  indexes: (imsi_hash), (device_id, observed_at DESC), (observed_at)
- `tracked_imsis`: id bigserial pk, imsi_hash text unique not null, imsi_encrypted bytea not null,
  label/notes text null, risk_level text null default 'low', first_seen/last_seen timestamptz default now(),
  is_active bool not null default true
- `alerts`: id bigserial pk, imsi_hash text null, device_id UUID null fk, type text not null,
  severity text not null default 'info', title text not null, message text null, ai_analysis text null,
  resolved bool not null default false, resolved_at timestamptz null, resolved_by text null,
  created_at timestamptz default now(); indexes (severity), (resolved), (created_at DESC)
- `audit_log`: id bigserial pk, actor text not null, action text not null, resource_type text null,
  resource_id text null, detail jsonb null, ip text null, created_at timestamptz default now()

## Endpoints (all under /api/v1; bind 127.0.0.1 — WireGuard comes in Phase B)
- `GET /api/v1/health` → `{"status":"ok","version":"0.1.0"}` (no auth)
- `POST /api/v1/devices/register` — header `X-Provisioning-Token` must equal PROVISIONING_TOKEN env value.
  Body: {name, lat, lng, altitude?, firmware_version?}. Generate device token `secrets.token_urlsafe(32)`,
  store sha256 hash, return it ONCE: 201 {device_id, device_token}. If name exists: update location/status,
  ROTATE token (new token), return 200 with new token.
- `POST /api/v1/devices/{device_id}/heartbeat` — header `X-Device-Token` (valid device). 204; sets last_seen, status online.
- `POST /api/v1/observations` — header `X-Device-Token`. Body {observations: [...]} max 200 items.
  Item: {imsi (required), mcc?, mnc?, lac?, cell_id?, country?, brand?, operator?, signal_dbm?, snr_db?,
  arfcn?, frequency?, tmsi1?, tmsi2?, observed_at? (ISO, default server now)}.
  Per item: strip spaces, validate imsi 5–20 digits else 422; encrypt + hash; dedup: skip when same
  device+imsi_hash seen within DEDUP_WINDOW_SECONDS (latest lookup); upsert tracked_imsis (new → insert +
  create alert type 'new_device', severity 'info' if country present else 'warning'); response
  201 {created: n, duplicates: m}. Unknown/bad token → 401 generic.
- `GET /api/v1/devices` — requires valid X-Device-Token or X-Provisioning-Token; returns id, name, lat, lng, status, last_seen.
- CLI retention: `uv run python -m app.cli retention --keep-days N [--purge]` — default dry-run lists count of
  observations older than N days; `--purge` deletes them and writes audit row (actor 'retention').

## Security rules (non-negotiable)
1. NO real secrets anywhere in source, tests, or fixtures — placeholders only. Tests generate their own
   crypto keys and tokens.
2. `.env.example` committed with placeholders and a comment showing how to generate the Fernet key:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. `.env` must never be committed.
4. Errors never echo tokens/keys; generic 401/500 messages.
5. Test/example IMSI values are fake, e.g. '123456789012345'.

## Tests — write FIRST (red → green), all must pass
- test_crypto: encrypt→decrypt round-trip; hash stable + unique per imsi; wrong key fails.
- test_auth: register without provisioning token → 401; observations with bad token → 401; heartbeat unknown device → 401.
- test_devices: register → 201 + token returned + persisted; existing name → token rotates → 200.
- test_observations: single + batch → 201 counts; dedup within window (no double insert, no duplicate alert);
  new IMSI → tracked_imsis + alert created; invalid imsi → 422.
- test_retention: seed rows older than keep-days; dry-run reports; --purge deletes only old rows + audit written.
- Integration tests hit the real Postgres container (DATABASE_URL from env in conftest, fresh schema per run).
- Test command: `cd backend && uv run pytest -q`

## Acceptance criteria (I will re-run every one myself — do not claim green without running)
1. `uv run pytest -q` green.
2. App boots: `cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`; GET /api/v1/health → 200.
3. `uv run alembic upgrade head` clean on a fresh schema (0001).
4. No secrets in tracked files (real token values / DB password absent from source and tests).
5. Document the exact curl commands for: register → heartbeat → post observation (single + batch) → verify
   DB rows + duplicate behavior, in a `backend/README.md` or in comments at the end of this spec.

## NOT in scope (do NOT touch)
frontend/, convex/, pi/, deploy/, server/ (old proxies), README.md, package.json.
No WireGuard (Phase B), no Crime AI API (Phase C), no dashboard/export (Phase C), no triangulation port (later).
Do NOT push to GitHub. Commit locally on branch `phase-a-server-backend` in logical commits.

## Implementation references (read-only)
convex/schema.ts (data shapes), convex/observations.ts, convex/devices.ts, convex/alerts.ts (business rules).