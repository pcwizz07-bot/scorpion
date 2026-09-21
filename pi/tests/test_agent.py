import json
import os
import stat

import pytest

from pi.agent import load_state, provision_if_needed, save_state
from pi.node.config import Config
from pi.node.transport import TransportAuthError


class _FakeTransport:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.calls = []

    def register(self, provisioning_token, name, lat, lng, firmware_version=None):
        self.calls.append((provisioning_token, name, lat, lng, firmware_version))
        if self._error is not None:
            raise self._error
        return self._response


def test_save_state_then_load_state_roundtrips(tmp_path):
    path = str(tmp_path / "state.json")

    save_state(path, {"device_id": "1", "device_token": "tok-1"})
    state = load_state(path)

    assert state == {"device_id": "1", "device_token": "tok-1"}


def test_save_state_sets_file_permissions_to_600(tmp_path):
    path = str(tmp_path / "state.json")

    save_state(path, {"device_id": "1", "device_token": "tok-1"})

    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600


def test_send_loop_survives_spool_lock_error(tmp_path):
    import sqlite3
    import threading

    from pi.node.spool import Spool

    from pi.agent import send_loop

    spool = Spool(str(tmp_path / "spool.db"))
    spool.append({"imsi": "111222333444555"})
    stop = threading.Event()
    calls = {"n": 0}

    def flaky_send_fn(device_id, device_token, observations):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sqlite3.OperationalError("database is locked")
        stop.set()
        return {"created": 1, "duplicates": 0}

    transport = _FakeTransport()
    send_loop(
        spool,
        transport,
        {"device_id": "d", "device_token": "t"},
        object(),
        str(tmp_path / "state.json"),
        stop,
        send_fn=flaky_send_fn,
    )

    # The transient lock error must not kill the sender: it retries and drains.
    assert calls["n"] == 2
    assert spool.pending() == []


def test_load_state_returns_none_when_file_missing(tmp_path):
    path = str(tmp_path / "missing.json")

    assert load_state(path) is None


def test_provision_if_needed_returns_existing_state_without_calling_transport(tmp_path):
    path = str(tmp_path / "state.json")
    save_state(path, {"device_id": "42", "device_token": "tok-42"})
    transport = _FakeTransport()
    config = Config(provisioning_token="prov-secret")

    device_id, device_token = provision_if_needed(config, transport, path)

    assert (device_id, device_token) == ("42", "tok-42")
    assert transport.calls == []


def test_provision_if_needed_registers_and_saves_state_when_no_state_file(tmp_path):
    path = str(tmp_path / "state.json")
    transport = _FakeTransport(response={"device_id": "7", "device_token": "tok-7"})
    config = Config(device_name="Pi-1", lat=1.0, lng=2.0, provisioning_token="prov-secret")

    device_id, device_token = provision_if_needed(config, transport, path)

    assert (device_id, device_token) == ("7", "tok-7")
    assert transport.calls == [("prov-secret", "Pi-1", 1.0, 2.0, None)]
    assert load_state(path) == {"device_id": "7", "device_token": "tok-7"}


def test_provision_if_needed_raises_without_state_or_provisioning_token(tmp_path):
    path = str(tmp_path / "state.json")
    transport = _FakeTransport()
    config = Config(provisioning_token=None)

    with pytest.raises(RuntimeError):
        provision_if_needed(config, transport, path)


def test_provision_if_needed_propagates_transport_auth_error(tmp_path):
    path = str(tmp_path / "state.json")
    transport = _FakeTransport(error=TransportAuthError("bad token"))
    config = Config(provisioning_token="prov-secret")

    with pytest.raises(TransportAuthError):
        provision_if_needed(config, transport, path)
