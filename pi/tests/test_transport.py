import http.server
import json
import threading

import pytest

from pi.node.spool import Spool
from pi.node.transport import (
    Transport,
    TransportAuthError,
    TransportRetryableError,
    flush,
    next_backoff_seconds,
)

PROVISIONING_TOKEN = "prov-secret"


class _FakeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length))

    def do_POST(self):
        state = self.server.state
        if self.path == "/api/v1/devices/register":
            if self.headers.get("X-Provisioning-Token") != PROVISIONING_TOKEN:
                self.send_response(401)
                self.end_headers()
                return
            device_id = str(state["next_device_id"])
            state["next_device_id"] += 1
            device_token = f"tok-{device_id}"
            state["devices"][device_id] = device_token
            self._send_json(201, {"device_id": device_id, "device_token": device_token})
            return

        if self.path.startswith("/api/v1/devices/") and self.path.endswith("/heartbeat"):
            device_id = self.path.split("/")[4]
            if state["devices"].get(device_id) != self.headers.get("X-Device-Token"):
                self.send_response(401)
                self.end_headers()
                return
            state["heartbeats"].append(device_id)
            self.send_response(204)
            self.end_headers()
            return

        if self.path == "/api/v1/observations":
            token = self.headers.get("X-Device-Token")
            if token not in state["devices"].values():
                self.send_response(401)
                self.end_headers()
                return
            if state["force_status"] is not None:
                self.send_response(state["force_status"])
                self.end_headers()
                return
            body = self._read_body()
            obs = body.get("observations", [])
            state["observations_batches"].append(obs)
            self._send_json(201, {"created": len(obs), "duplicates": 0})
            return

        self.send_response(404)
        self.end_headers()


@pytest.fixture
def fake_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _FakeHandler)
    server.state = {
        "devices": {},
        "next_device_id": 1,
        "heartbeats": [],
        "observations_batches": [],
        "force_status": None,
    }
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    thread.join()


def server_url(server):
    return f"http://127.0.0.1:{server.server_address[1]}"


def test_register_happy_path(fake_server):
    transport = Transport(server_url(fake_server))

    result = transport.register(PROVISIONING_TOKEN, name="Pi-1", lat=1.0, lng=2.0, firmware_version="v1")

    assert result["device_id"] == "1"
    assert result["device_token"] == "tok-1"


def test_register_bad_token_raises_auth_error(fake_server):
    transport = Transport(server_url(fake_server))

    with pytest.raises(TransportAuthError):
        transport.register("wrong-token", name="Pi-1", lat=1.0, lng=2.0)


def test_heartbeat_happy_path(fake_server):
    transport = Transport(server_url(fake_server))
    reg = transport.register(PROVISIONING_TOKEN, name="Pi-1", lat=1.0, lng=2.0)

    transport.heartbeat(reg["device_id"], reg["device_token"])

    assert fake_server.state["heartbeats"] == [reg["device_id"]]


def test_send_observations_happy_path(fake_server):
    transport = Transport(server_url(fake_server))
    reg = transport.register(PROVISIONING_TOKEN, name="Pi-1", lat=1.0, lng=2.0)

    result = transport.send_observations(
        reg["device_id"], reg["device_token"], [{"imsi": "111222333444555"}]
    )

    assert result == {"created": 1, "duplicates": 0}
    assert fake_server.state["observations_batches"] == [[{"imsi": "111222333444555"}]]


def test_send_observations_splits_batch_at_200(fake_server):
    transport = Transport(server_url(fake_server))
    reg = transport.register(PROVISIONING_TOKEN, name="Pi-1", lat=1.0, lng=2.0)
    observations = [{"imsi": str(111222333444000 + i)} for i in range(250)]

    result = transport.send_observations(reg["device_id"], reg["device_token"], observations)

    assert result == {"created": 250, "duplicates": 0}
    batch_sizes = [len(b) for b in fake_server.state["observations_batches"]]
    assert batch_sizes == [200, 50]


def test_send_observations_401_raises_auth_error(fake_server):
    transport = Transport(server_url(fake_server))

    with pytest.raises(TransportAuthError):
        transport.send_observations("1", "bad-token", [{"imsi": "111222333444555"}])


def test_send_observations_500_raises_retryable_error(fake_server):
    transport = Transport(server_url(fake_server))
    reg = transport.register(PROVISIONING_TOKEN, name="Pi-1", lat=1.0, lng=2.0)
    fake_server.state["force_status"] = 500

    with pytest.raises(TransportRetryableError):
        transport.send_observations(reg["device_id"], reg["device_token"], [{"imsi": "111222333444555"}])


def test_send_observations_network_down_raises_retryable_error():
    transport = Transport("http://127.0.0.1:1", timeout=1.0)

    with pytest.raises(TransportRetryableError):
        transport.send_observations("1", "tok", [{"imsi": "111222333444555"}])


def test_next_backoff_seconds_doubles_and_caps_at_60():
    delay = None
    delays = []
    for _ in range(8):
        delay = next_backoff_seconds(delay)
        delays.append(delay)

    assert delays == [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]


def test_flush_drains_spool_on_success(fake_server, tmp_path):
    transport = Transport(server_url(fake_server))
    reg = transport.register(PROVISIONING_TOKEN, name="Pi-1", lat=1.0, lng=2.0)
    spool = Spool(str(tmp_path / "spool.db"))
    spool.append({"imsi": "111222333444555"})

    result = flush(spool, transport, reg["device_id"], reg["device_token"])

    assert result == {"sent": 1, "created": 1, "duplicates": 0}
    assert spool.pending() == []


def test_flush_leaves_spool_queued_when_server_down(tmp_path):
    transport = Transport("http://127.0.0.1:1", timeout=1.0)
    spool = Spool(str(tmp_path / "spool.db"))
    spool.append({"imsi": "111222333444555"})

    with pytest.raises(TransportRetryableError):
        flush(spool, transport, "1", "tok")

    pending = spool.pending()
    assert len(pending) == 1
    assert pending[0]["attempts"] == 1
