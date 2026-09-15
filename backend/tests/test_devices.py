from app.models import Device


def test_register_creates_device_and_returns_token(client, provisioning_token, db_session):
    resp = client.post(
        "/api/v1/devices/register",
        json={"name": "pi-north", "lat": 1.23, "lng": 4.56},
        headers={"X-Provisioning-Token": provisioning_token},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "device_id" in body
    assert len(body["device_token"]) > 20

    device = db_session.query(Device).filter(Device.name == "pi-north").one()
    assert str(device.id) == body["device_id"]
    assert device.device_token_hash != body["device_token"]


def test_register_existing_name_rotates_token(client, provisioning_token):
    first = client.post(
        "/api/v1/devices/register",
        json={"name": "pi-south", "lat": 1.0, "lng": 2.0},
        headers={"X-Provisioning-Token": provisioning_token},
    )
    assert first.status_code == 201
    first_token = first.json()["device_token"]

    second = client.post(
        "/api/v1/devices/register",
        json={"name": "pi-south", "lat": 1.5, "lng": 2.5},
        headers={"X-Provisioning-Token": provisioning_token},
    )
    assert second.status_code == 200
    second_token = second.json()["device_token"]
    assert second_token != first_token
    assert second.json()["device_id"] == first.json()["device_id"]

    old_token_heartbeat = client.post(
        f"/api/v1/devices/{first.json()['device_id']}/heartbeat",
        headers={"X-Device-Token": first_token},
    )
    assert old_token_heartbeat.status_code == 401

    new_token_heartbeat = client.post(
        f"/api/v1/devices/{first.json()['device_id']}/heartbeat",
        headers={"X-Device-Token": second_token},
    )
    assert new_token_heartbeat.status_code == 204
