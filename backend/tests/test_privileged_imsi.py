"""Privileged IMSI visibility: full IMSI only for provisioning-token logins.

Device tokens (capture nodes) must keep seeing masked IMSIs only.
The portal (Francois's login) and server automation use the provisioning
token and may see the decrypted, full IMSI for identification.
"""


def _post_observation(client, device_token: str, imsi: str) -> None:
    resp = client.post(
        "/api/v1/observations",
        json={
            "observations": [
                {
                    "imsi": imsi,
                    "mcc": "655",
                    "mnc": "01",
                    "country": "ZA",
                    "brand": "Vodacom",
                    "operator": "Vodacom",
                }
            ]
        },
        headers={"X-Device-Token": device_token},
    )
    assert resp.status_code == 201, resp.text


def test_device_token_list_masked_only(client, registered_device):
    _post_observation(client, registered_device["device_token"], "655010123456789")

    resp = client.get(
        "/api/v1/observations?limit=50",
        headers={"X-Device-Token": registered_device["device_token"]},
    )
    assert resp.status_code == 200
    row = resp.json()[0]
    # Device token: NEVER the decrypted IMSI.
    assert row["imsi_masked"] == "655010***89"
    assert row["imsi"] is None


def test_provisioning_token_list_full_imsi(client, registered_device, provisioning_token):
    _post_observation(client, registered_device["device_token"], "655010123456789")

    resp = client.get(
        "/api/v1/observations?limit=50",
        headers={"X-Provisioning-Token": provisioning_token},
    )
    assert resp.status_code == 200
    row = resp.json()[0]
    # Provisioning (server/admin) login: decrypted full IMSI for identification.
    assert row["imsi"] == "655010123456789"
    assert row["imsi_masked"] == "655010***89"


def test_unauthorized_list_401(client):
    resp = client.get("/api/v1/observations?limit=50")
    assert resp.status_code == 401