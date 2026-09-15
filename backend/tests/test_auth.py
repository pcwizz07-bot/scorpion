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
