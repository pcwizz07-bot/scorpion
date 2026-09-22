import uuid


def test_register_without_provisioning_token_401(client):
    resp = client.post("/api/v1/devices/register", json={"name": "x", "lat": 0, "lng": 0})
    assert resp.status_code == 401


def test_register_with_bad_provisioning_token_401(client):
    resp = client.post(
        "/api/v1/devices/register",
        json={"name": "x", "lat": 0, "lng": 0},
        headers={"X-Provisioning-Token": "wrong-token"},
    )
    assert resp.status_code == 401


def test_observations_with_bad_device_token_401(client):
    resp = client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": "123456789012345"}]},
        headers={"X-Device-Token": "not-a-real-token"},
    )
    assert resp.status_code == 401


def test_heartbeat_unknown_device_401(client):
    resp = client.post(
        f"/api/v1/devices/{uuid.uuid4()}/heartbeat",
        headers={"X-Device-Token": "not-a-real-token"},
    )
    assert resp.status_code == 401


# --- login + TOTP session auth ---

from datetime import datetime, timedelta, timezone  # noqa: E402

from app.auth_security import _totp_code_at, generate_totp_secret, hash_password  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import AuthSession, User  # noqa: E402


def _make_user(secret: str) -> None:
    db = SessionLocal()
    try:
        db.add(User(username="admin", password_hash=hash_password("hunter2"), totp_secret=secret))
        db.commit()
    finally:
        db.close()


def _code(secret: str) -> str:
    import time

    return _totp_code_at(secret, int(time.time()))


def test_auth_requires_totp(client):
    secret = generate_totp_secret()
    _make_user(secret)

    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "hunter2", "totp_code": "000000"})
    assert resp.status_code == 401


def test_login_wrong_password(client):
    secret = generate_totp_secret()
    _make_user(secret)

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong", "totp_code": _code(secret)},
    )
    assert resp.status_code == 401


def test_login_success_and_session_grants_provisioning(client, registered_device):
    secret = generate_totp_secret()
    _make_user(secret)
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": "655010123456789"}]},
        headers={"X-Device-Token": registered_device["device_token"]},
    )

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "hunter2", "totp_code": _code(secret)},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]

    # A session token acts as the provisioning token: full IMSI exposed.
    rows = client.get("/api/v1/observations", headers={"X-Provisioning-Token": token}).json()
    assert rows[0]["imsi"] == "655010123456789"


def test_logout_invalidates_session(client):
    secret = generate_totp_secret()
    _make_user(secret)
    token = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "hunter2", "totp_code": _code(secret)},
    ).json()["token"]

    assert client.post("/api/v1/auth/logout", headers={"X-Provisioning-Token": token}).status_code == 204
    assert client.get("/api/v1/auth/status", headers={"X-Provisioning-Token": token}).json()["authenticated"] is False


def test_session_expired_rejected(client):
    secret = generate_totp_secret()
    _make_user(secret)
    token = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "hunter2", "totp_code": _code(secret)},
    ).json()["token"]

    db = SessionLocal()
    try:
        session = db.query(AuthSession).one()
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    assert client.get("/api/v1/auth/status", headers={"X-Provisioning-Token": token}).json()["authenticated"] is False
