"""LTE ingest endpoints: cell sightings + identities (encrypted, masked reads)."""


def _device_headers(registered_device):
    return {"X-Device-Token": registered_device["device_token"]}


def _provisioning_headers(token):
    return {"X-Provisioning-Token": token}


def test_lte_cells_post_and_list(client, registered_device):
    resp = client.post(
        "/api/v1/lte/cells",
        json={
            "cells": [
                {"pci": 79, "tac": 1234, "band": 8, "earfcn": 3460, "freq_mhz": 944.6, "plmn": "655-01", "signal_dbm": -71}
            ]
        },
        headers=_device_headers(registered_device),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"created": 1}

    resp = client.get("/api/v1/lte/cells", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    row = resp.json()[0]
    assert row["pci"] == 79
    assert row["tac"] == 1234
    assert row["freq_mhz"] == 944.6
    assert row["device_name"] == "test-device"


def test_lte_cells_requires_auth(client):
    assert client.get("/api/v1/lte/cells").status_code == 401
    resp = client.post("/api/v1/lte/cells", json={"cells": [{"pci": 1}]})
    assert resp.status_code == 401


def test_lte_cells_energy_only_pci_null(client, registered_device):
    resp = client.post(
        "/api/v1/lte/cells",
        json={"cells": [{"freq_mhz": 944.7, "signal_dbm": -60, "band": 8, "earfcn": 3647}]},
        headers=_device_headers(registered_device),
    )
    assert resp.status_code == 201, resp.text

    row = client.get("/api/v1/lte/cells", headers=_device_headers(registered_device)).json()[0]
    assert row["pci"] is None
    assert row["freq_mhz"] == 944.7
    assert row["signal_dbm"] == -60


def test_lte_identity_post_and_device_list_masked(client, registered_device):
    resp = client.post(
        "/api/v1/lte/identities",
        json={
            "identities": [
                {"kind": "imsi", "value": "655010123456789", "s_tmsi": "0x1a2b3c4d", "pci": 79, "tac": 1234, "band": 8}
            ]
        },
        headers=_device_headers(registered_device),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"created": 1, "duplicates": 0}

    resp = client.get("/api/v1/lte/identities", headers=_device_headers(registered_device))
    assert resp.status_code == 200
    row = resp.json()[0]
    assert row["value_masked"] == "655010***89"
    assert row["value"] is None
    assert row["s_tmsi"] == "0x1a2b3c4d"
    assert row["pci"] == 79


def test_lte_identity_provisioning_list_full_value(client, registered_device, provisioning_token):
    client.post(
        "/api/v1/lte/identities",
        json={"identities": [{"kind": "imei", "value": "990000862471854"}]},
        headers=_device_headers(registered_device),
    )

    resp = client.get("/api/v1/lte/identities", headers=_provisioning_headers(provisioning_token))
    assert resp.status_code == 200
    row = resp.json()[0]
    assert row["value"] == "990000862471854"
    assert row["value_masked"] == "990000***54"


def test_lte_identity_invalid_value_422(client, registered_device):
    resp = client.post(
        "/api/v1/lte/identities",
        json={"identities": [{"kind": "imsi", "value": "abc"}]},
        headers=_device_headers(registered_device),
    )
    assert resp.status_code == 422


def test_lte_identity_requires_auth(client):
    assert client.get("/api/v1/lte/identities").status_code == 401