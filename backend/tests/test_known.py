"""Known-identity registry: label captures, rule out own devices."""


def _device_headers(registered_device):
    return {"X-Device-Token": registered_device["device_token"]}


def _provisioning_headers(token):
    return {"X-Provisioning-Token": token}


def _post_observation(client, registered_device):
    client.post(
        "/api/v1/observations",
        json={"observations": [{"imsi": "655010123456789"}]},
        headers=_device_headers(registered_device),
    )


def test_known_requires_provisioning(client, registered_device, provisioning_token):
    resp = client.post(
        "/api/v1/known",
        json={"kind": "imsi", "value": "655010123456789", "label": "Francois phone", "is_own": True},
        headers=_device_headers(registered_device),
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/known",
        json={"kind": "imsi", "value": "655010123456789", "label": "Francois phone", "is_own": True},
        headers=_provisioning_headers(provisioning_token),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["label"] == "Francois phone"
    assert resp.json()["is_own"] is True


def test_known_upsert_updates_label(client, provisioning_token, registered_device):
    headers = _provisioning_headers(provisioning_token)
    client.post("/api/v1/known", json={"kind": "imsi", "value": "655010123456789", "label": "old", "is_own": False}, headers=headers)
    resp = client.post("/api/v1/known", json={"kind": "imsi", "value": "655010123456789", "label": "new", "is_own": True}, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["label"] == "new"
    rows = client.get("/api/v1/known", headers=headers).json()
    assert len(rows) == 1


def test_observations_carry_known_label(client, provisioning_token, registered_device):
    _post_observation(client, registered_device)
    client.post(
        "/api/v1/known",
        json={"kind": "imsi", "value": "655010123456789", "label": "own phone", "is_own": True},
        headers=_provisioning_headers(provisioning_token),
    )

    rows = client.get("/api/v1/observations", headers=_provisioning_headers(provisioning_token)).json()
    assert rows[0]["known"] == "own phone"


def test_lte_identities_carry_known_label(client, provisioning_token, registered_device):
    client.post(
        "/api/v1/lte/identities",
        json={"identities": [{"kind": "imsi", "value": "990000862471854"}]},
        headers=_device_headers(registered_device),
    )
    client.post(
        "/api/v1/known",
        json={"kind": "imsi", "value": "990000862471854", "label": "field phone"},
        headers=_provisioning_headers(provisioning_token),
    )

    rows = client.get("/api/v1/lte/identities", headers=_provisioning_headers(provisioning_token)).json()
    assert rows[0]["known"] == "field phone"


def test_known_delete(client, provisioning_token):
    headers = _provisioning_headers(provisioning_token)
    row = client.post("/api/v1/known", json={"kind": "imsi", "value": "655010123456789", "label": "x"}, headers=headers).json()
    resp = client.delete(f"/api/v1/known/{row['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/api/v1/known", headers=headers).json() == []