from datetime import datetime, timedelta, timezone

FAKE_IMSI_1 = "123456789012345"
FAKE_IMSI_2 = "223456789012346"


def _device_headers(registered_device):
    return {"X-Device-Token": registered_device["device_token"]}


def _provisioning_headers(provisioning_token):
    return {"X-Provisioning-Token": provisioning_token}


def test_stats_requires_auth(client):
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 401


def test_stats_accepts_provisioning_token(client, provisioning_token):
    resp = client.get("/api/v1/stats", headers=_provisioning_headers(provisioning_token))
    assert resp.status_code == 200


def test_stats_returns_expected_counts(client, registered_device, db_session):
    headers = _device_headers(registered_device)

    # two observations for the same IMSI (dedup window applies) -> one tracked IMSI
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1, "country": "KE"}]},
        headers=headers,
    )
    # a second, distinct IMSI, observed far enough in the past to be outside 24h
    old_time = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_2, "country": "TZ", "observed_at": old_time}]},
        headers=headers,
    )

    resp = client.get("/api/v1/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["devices_total"] == 1
    assert body["devices_online"] == 1
    assert body["observations_total"] == 2
    assert body["observations_last_24h"] == 1
    assert body["unique_imsis"] == 2
    assert body["tracked_active"] == 2
    # device-registration alert + one new_device alert per distinct IMSI
    assert body["alerts_total"] == 3
    assert body["alerts_open"] == 3

    for field in (
        "devices_total",
        "devices_online",
        "observations_total",
        "observations_last_24h",
        "unique_imsis",
        "tracked_active",
        "alerts_total",
        "alerts_open",
    ):
        assert field in body


def test_stats_counts_resolved_alerts_as_not_open(client, registered_device, db_session):
    headers = _device_headers(registered_device)
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}]},
        headers=headers,
    )
    from app.models import Alert

    db_session.query(Alert).update({"resolved": True})
    db_session.commit()

    resp = client.get("/api/v1/stats", headers=headers)
    body = resp.json()
    assert body["alerts_total"] == 2
    assert body["alerts_open"] == 0
