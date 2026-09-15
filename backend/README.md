# Scorpion backend (Phase A)

FastAPI + PostgreSQL server, self-hosted replacement for the Convex backend.
See `docs/superpowers/specs/2026-09-15-server-phase-a.md` for the full spec.

## Setup

```bash
cd backend
uv sync
cp .env.example .env   # then edit .env with real local-dev values
uv run alembic upgrade head
```

## Run

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Test

```bash
uv run pytest -q
```

Tests hit the real PostgreSQL container (`DATABASE_URL` from the environment)
and create/drop a fresh schema around every test.

## Retention CLI

```bash
uv run python -m app.cli retention --keep-days 90            # dry run
uv run python -m app.cli retention --keep-days 90 --purge     # deletes + audit row
```

## Manual walkthrough (curl)

Load real local values first:

```bash
set -a && source .env && set +a
```

1. Register a device (rotates the token if the name already exists):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/devices/register \
  -H "X-Provisioning-Token: $PROVISIONING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"pi-demo","lat":-1.28,"lng":36.82,"firmware_version":"0.1.0"}'
# => 201 {"device_id": "...", "device_token": "..."}
```

Save the two fields as `DEVICE_ID` and `DEVICE_TOKEN` for the next calls.

2. Heartbeat:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "http://127.0.0.1:8000/api/v1/devices/$DEVICE_ID/heartbeat" \
  -H "X-Device-Token: $DEVICE_TOKEN"
# => 204
```

3. Post a single observation:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/observations \
  -H "X-Device-Token: $DEVICE_TOKEN" -H "Content-Type: application/json" \
  -d '{"observations":[{"imsi":"123456789012345","country":"KE","brand":"Safaricom"}]}'
# => 201 {"created": 1, "duplicates": 0}
```

4. Post the same observation again within `DEDUP_WINDOW_SECONDS` (default 60s)
   — it is counted as a duplicate, not re-inserted:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/observations \
  -H "X-Device-Token: $DEVICE_TOKEN" -H "Content-Type: application/json" \
  -d '{"observations":[{"imsi":"123456789012345","country":"KE","brand":"Safaricom"}]}'
# => 201 {"created": 0, "duplicates": 1}
```

5. Post a batch of new observations:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/observations \
  -H "X-Device-Token: $DEVICE_TOKEN" -H "Content-Type: application/json" \
  -d '{"observations":[{"imsi":"223456789012345","country":"TZ"},{"imsi":"323456789012345"}]}'
# => 201 {"created": 2, "duplicates": 0}
```

6. List devices (either a device token or the provisioning token works):

```bash
curl -s http://127.0.0.1:8000/api/v1/devices -H "X-Device-Token: $DEVICE_TOKEN"
```

7. Verify DB rows directly:

```bash
uv run python -c "
from app.db import SessionLocal
from app.models import ImsiObservation, TrackedImsi, Alert, Device
db = SessionLocal()
print('devices:', db.query(Device).count())
print('observations:', db.query(ImsiObservation).count())
print('tracked_imsis:', db.query(TrackedImsi).count())
print('alerts:', db.query(Alert).count())
"
```

With the walkthrough above this reports 1 device, 3 observations (the
duplicate is skipped), 3 tracked IMSIs, and 4 alerts (one `new_device` alert
for the device registration, three for the new IMSIs).
