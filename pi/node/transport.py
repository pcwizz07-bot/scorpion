"""Register/heartbeat/observations batch via urllib; backoff logic."""
import json
import urllib.error
import urllib.request

MAX_BATCH_SIZE = 200
MAX_BACKOFF_SECONDS = 60.0


class TransportAuthError(Exception):
    pass


class TransportRetryableError(Exception):
    pass


def next_backoff_seconds(previous: float | None) -> float:
    if previous is None:
        return 1.0
    return min(previous * 2, MAX_BACKOFF_SECONDS)


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


class Transport:
    def __init__(self, server_url: str, timeout: float = 10.0):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, body: dict, headers: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            self.server_url + path,
            data=data,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise TransportAuthError("unauthorized") from e
            raise TransportRetryableError(f"http error {e.code}") from e
        except urllib.error.URLError as e:
            raise TransportRetryableError(f"network error {e.reason}") from e

    def register(self, provisioning_token: str, name: str, lat: float, lng: float, firmware_version: str | None = None) -> dict:
        body = {"name": name, "lat": lat, "lng": lng, "firmware_version": firmware_version}
        return self._post("/api/v1/devices/register", body, {"X-Provisioning-Token": provisioning_token})

    def heartbeat(self, device_id: str, device_token: str) -> None:
        self._post(f"/api/v1/devices/{device_id}/heartbeat", {}, {"X-Device-Token": device_token})

    def send_observations(self, device_id: str, device_token: str, observations: list) -> dict:
        created = 0
        duplicates = 0
        for chunk in _chunks(observations, MAX_BATCH_SIZE):
            payload = self._post(
                "/api/v1/observations",
                {"observations": chunk},
                {"X-Device-Token": device_token},
            )
            created += payload.get("created", 0)
            duplicates += payload.get("duplicates", 0)
        return {"created": created, "duplicates": duplicates}


def flush(spool, transport: Transport, device_id: str, device_token: str, batch_size: int = MAX_BATCH_SIZE) -> dict:
    """Send pending spool observations; mark sent+delete on success only.

    On failure the spool is left untouched (still queued) so nothing is
    lost, and each pending row's attempt counter is bumped for backoff.
    """
    pending = spool.pending(limit=batch_size)
    if not pending:
        return {"sent": 0, "created": 0, "duplicates": 0}

    ids = [row["id"] for row in pending]
    observations = [row["observation"] for row in pending]
    try:
        result = transport.send_observations(device_id, device_token, observations)
    except (TransportAuthError, TransportRetryableError):
        spool.record_attempt(ids)
        raise

    spool.mark_sent(ids)
    spool.delete(ids)
    return {"sent": len(ids), "created": result["created"], "duplicates": result["duplicates"]}
