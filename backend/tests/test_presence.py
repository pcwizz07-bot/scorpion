from app.models import PresenceEvent


def _headers(registered_device):
    return {"X-Device-Token": registered_device["device_token"]}


def test_single_presence_event_created(client, registered_device, db_session):
    resp = client.post(
        "/api/v1/presence",
        json={"events": [{"kind": "plu", "tmsi_old": "aabbccdd", "lac": 42}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 201
    assert resp.json() == {"created": 1, "duplicates": 0}
    assert db_session.query(PresenceEvent).count() == 1


def test_reauth_event_stores_old_and_new_tmsi(client, registered_device, db_session):
    resp = client.post(
        "/api/v1/presence",
        json={"events": [{"kind": "reauth", "tmsi_old": "11223344", "tmsi_new": "aabbccdd", "lac": 42}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 201
    row = db_session.query(PresenceEvent).one()
    assert row.tmsi_old == "11223344"
    assert row.tmsi_new == "aabbccdd"
    assert row.kind == "reauth"


def test_dedup_within_window_skips_duplicate(client, registered_device, db_session):
    body = {"events": [{"kind": "page", "tmsi_old": "11223344"}]}
    client.post("/api/v1/presence", json=body, headers=_headers(registered_device))
    resp = client.post("/api/v1/presence", json=body, headers=_headers(registered_device))

    assert resp.status_code == 201
    assert resp.json() == {"created": 0, "duplicates": 1}
    assert db_session.query(PresenceEvent).count() == 1


def test_invalid_kind_422(client, registered_device):
    resp = client.post(
        "/api/v1/presence",
        json={"events": [{"kind": "bogus"}]},
        headers=_headers(registered_device),
    )
    assert resp.status_code == 422


def test_missing_device_token_401(client):
    resp = client.post("/api/v1/presence", json={"events": [{"kind": "plu"}]})
    assert resp.status_code == 401


def test_list_presence_events_requires_auth(client):
    resp = client.get("/api/v1/presence")
    assert resp.status_code == 401


def test_list_presence_events_returns_created_events(client, registered_device, provisioning_token):
    client.post(
        "/api/v1/presence",
        json={"events": [{"kind": "attach", "tmsi_old": "deadbeef"}]},
        headers=_headers(registered_device),
    )

    resp = client.get("/api/v1/presence", headers={"X-Provisioning-Token": provisioning_token})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["kind"] == "attach"
    assert body[0]["tmsi_old"] == "deadbeef"
    assert body[0]["device_id"] == registered_device["device_id"]


def test_list_presence_events_filters_by_device_id(client, registered_device, provisioning_token):
    client.post(
        "/api/v1/presence",
        json={"events": [{"kind": "page", "tmsi_old": "11223344"}]},
        headers=_headers(registered_device),
    )

    resp = client.get(
        "/api/v1/presence",
        params={"device_id": "00000000-0000-0000-0000-000000000000"},
        headers={"X-Provisioning-Token": provisioning_token},
    )

    assert resp.status_code == 200
    assert resp.json() == []
