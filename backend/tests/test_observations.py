from app.models import Alert, ImsiObservation, TrackedImsi

FAKE_IMSI_1 = "123456789012345"
FAKE_IMSI_2 = "123456789012346"


def _headers(registered_device):
    return {"X-Device-Token": registered_device["device_token"]}


def test_single_observation_created(client, registered_device, db_session):
    resp = client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1, "country": "KE", "brand": "Safaricom"}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 201
    assert resp.json() == {"created": 1, "duplicates": 0}

    assert db_session.query(ImsiObservation).count() == 1
    assert db_session.query(TrackedImsi).count() == 1
    assert db_session.query(Alert).filter(Alert.imsi_hash.isnot(None)).count() == 1


def test_batch_observation_counts(client, registered_device):
    resp = client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}, {"imsi": FAKE_IMSI_2}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 201
    assert resp.json() == {"created": 2, "duplicates": 0}


def test_dedup_within_window_skips_duplicate(client, registered_device, db_session):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1, "country": "KE"}]},
        headers=_headers(registered_device),
    )
    resp = client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1, "country": "KE"}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 201
    assert resp.json() == {"created": 0, "duplicates": 1}

    assert db_session.query(ImsiObservation).count() == 1
    assert db_session.query(Alert).filter(Alert.imsi_hash.isnot(None)).count() == 1


def test_new_imsi_creates_tracked_and_alert(client, registered_device, db_session):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": FAKE_IMSI_1}]},
        headers=_headers(registered_device),
    )
    tracked = db_session.query(TrackedImsi).one()
    assert tracked.is_active is True

    alert = db_session.query(Alert).filter(Alert.imsi_hash.isnot(None)).one()
    assert alert.severity == "warning"


def test_invalid_imsi_422(client, registered_device):
    resp = client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": "abc"}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 422
