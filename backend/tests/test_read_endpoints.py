from app.audit import write_audit
from app.crypto import imsi_encrypt, imsi_hash
from app.models import Alert, ImsiObservation, TrackedImsi

FAKE_IMSI_1 = "123456789012345"
FAKE_IMSI_2 = "223456789012346"


def _device_headers(registered_device):
    return {"X-Device-Token": registered_device["device_token"]}


def _provisioning_headers(provisioning_token):
    return {"X-Provisioning-Token": provisioning_token}


# --- /api/v1/observations ---


def test_observations_requires_auth(client):
    resp = client.get("/api/v1/observations")
    assert resp.status_code == 401


def test_observations_masks_imsi_and_orders_newest_first(client, registered_device, db_session):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1, "country": "KE"}]},
        headers=_device_headers(registered_device),
    )
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_2, "country": "TZ", "signal_dbm": -77}]},
        headers=_device_headers(registered_device),
    )

    resp = client.get("/api/v1/observations", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # newest first: the second-posted IMSI (FAKE_IMSI_2) comes first
    assert body[0]["imsi_masked"] == "223456***46"
    assert body[1]["imsi_masked"] == "123456***45"
    assert "imsi" not in body[0]
    assert "imsi_encrypted" not in body[0]
    assert body[0]["country"] == "TZ"
    assert body[0]["device_id"] == registered_device["device_id"]
    assert body[0]["device_name"] == "test-device"
    assert body[0]["signal_dbm"] == -77
    for field in (
        "id",
        "device_id",
        "device_name",
        "imsi_masked",
        "mcc",
        "mnc",
        "lac",
        "cell_id",
        "country",
        "brand",
        "operator",
        "signal_dbm",
        "observed_at",
    ):
        assert field in body[0]


def test_observations_response_never_leaks_full_imsi(client, registered_device):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}, {"imsi": FAKE_IMSI_2}]},
        headers=_device_headers(registered_device),
    )
    resp = client.get("/api/v1/observations", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    assert FAKE_IMSI_1 not in resp.text
    assert FAKE_IMSI_2 not in resp.text


def test_observations_respects_limit(client, registered_device):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}, {"imsi": FAKE_IMSI_2}]},
        headers=_device_headers(registered_device),
    )
    resp = client.get("/api/v1/observations?limit=1", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_observations_filters_by_device_id(client, registered_device, provisioning_token):
    other = client.post(
        "/api/v1/devices/register",
        json={"name": "other-device", "lat": 0.0, "lng": 0.0},
        headers=_provisioning_headers(provisioning_token),
    ).json()

    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}]},
        headers=_device_headers(registered_device),
    )
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_2}]},
        headers={"X-Device-Token": other["device_token"]},
    )

    resp = client.get(
        f"/api/v1/observations?device_id={other['device_id']}",
        headers=_provisioning_headers(provisioning_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["device_id"] == other["device_id"]


def test_observations_accepts_provisioning_token(client, provisioning_token):
    resp = client.get("/api/v1/observations", headers=_provisioning_headers(provisioning_token))
    assert resp.status_code == 200
    assert resp.json() == []


# --- /api/v1/alerts ---


def test_alerts_requires_auth(client):
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 401


def test_alerts_masks_imsi_when_present_and_orders_newest_first(client, registered_device):
    # device registration alert (no imsi) happens first
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}]},
        headers=_device_headers(registered_device),
    )

    resp = client.get("/api/v1/alerts", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # newest first: the new_device-imsi alert comes before the device-registration alert
    assert body[0]["imsi_masked"] == "123456***45"
    assert body[1]["imsi_masked"] is None
    assert body[0]["type"] == "new_device"
    assert body[0]["resolved"] is False
    for field in ("id", "device_id", "imsi_masked", "type", "severity", "title", "message", "resolved", "created_at"):
        assert field in body[0]


def test_alerts_response_never_leaks_full_imsi(client, registered_device):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}]},
        headers=_device_headers(registered_device),
    )
    resp = client.get("/api/v1/alerts", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    assert FAKE_IMSI_1 not in resp.text


def test_alerts_respects_limit(client, registered_device):
    resp = client.get("/api/v1/alerts?limit=1", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_alerts_accepts_provisioning_token(client, provisioning_token):
    resp = client.get("/api/v1/alerts", headers=_provisioning_headers(provisioning_token))
    assert resp.status_code == 200


# --- /api/v1/audit ---


def test_audit_requires_provisioning_token(client):
    resp = client.get("/api/v1/audit")
    assert resp.status_code == 401


def test_audit_rejects_device_token(client, registered_device):
    resp = client.get("/api/v1/audit", headers=_device_headers(registered_device))
    assert resp.status_code == 403


def test_audit_returns_rows_newest_first(client, provisioning_token, db_session):
    write_audit(db_session, actor="system", action="first_action")
    write_audit(db_session, actor="system", action="second_action")

    resp = client.get("/api/v1/audit", headers=_provisioning_headers(provisioning_token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["action"] == "second_action"
    assert body[1]["action"] == "first_action"
    for field in ("id", "action", "detail", "created_at"):
        assert field in body[0]


def test_audit_respects_limit(client, provisioning_token, db_session):
    write_audit(db_session, actor="system", action="first_action")
    write_audit(db_session, actor="system", action="second_action")

    resp = client.get("/api/v1/audit?limit=1", headers=_provisioning_headers(provisioning_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
