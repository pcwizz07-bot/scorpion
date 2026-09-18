#!/usr/bin/env python3
"""Scorpion Pi node agent: entry point, config, threads, signal handling."""
import json
import os
import signal
import sys
import threading
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from pi.node import capture, gnss, presence
from pi.node.config import DEFAULT_CONFIG_PATH, load_config
from pi.node.spool import Spool
from pi.node.transport import Transport, TransportAuthError, TransportRetryableError, flush, next_backoff_seconds

IDLE_POLL_S = 2.0


def load_state(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_state(path: str, state: dict) -> None:
    dir_ = os.path.dirname(path)
    if dir_:
        os.makedirs(dir_, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f)
    os.chmod(path, 0o600)


def provision_if_needed(cfg, transport: Transport, state_path: str) -> tuple:
    state = load_state(state_path)
    if state is not None and "device_id" in state and "device_token" in state:
        return state["device_id"], state["device_token"]

    if not cfg.provisioning_token:
        raise RuntimeError(
            "no state file at %s and no SCORPION_PROVISIONING_TOKEN set; cannot provision" % state_path
        )

    result = transport.register(
        cfg.provisioning_token, name=cfg.device_name, lat=cfg.lat, lng=cfg.lng, firmware_version=None
    )
    save_state(state_path, {"device_id": result["device_id"], "device_token": result["device_token"]})
    return result["device_id"], result["device_token"]


def reprovision(cfg, transport: Transport, state_path: str) -> tuple:
    if os.path.isfile(state_path):
        os.remove(state_path)
    return provision_if_needed(cfg, transport, state_path)


def heartbeat_loop(transport: Transport, identity: dict, interval_s: float, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            transport.heartbeat(identity["device_id"], identity["device_token"])
        except (TransportAuthError, TransportRetryableError):
            pass
        stop_event.wait(interval_s)


def capture_loop(
    reader: capture.TailReader,
    spool: Spool,
    device_name: str,
    get_fix,
    poll_interval_s: float,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        capture.capture_new_observations(reader, spool, device_name, get_fix=get_fix)
        stop_event.wait(poll_interval_s)


def presence_capture_loop(
    reader: capture.TailReader,
    spool: Spool,
    device_name: str,
    poll_interval_s: float,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        presence.capture_new_presence_events(reader, spool, device_name)
        stop_event.wait(poll_interval_s)


def send_loop(
    spool: Spool,
    transport: Transport,
    identity: dict,
    cfg,
    state_path: str,
    stop_event: threading.Event,
    send_fn=None,
) -> None:
    """Drain the spool with exponential backoff (1s..60s) on failure.

    ponytail: identity dict is read/written across threads without a lock;
    the GIL makes single-key read/write atomic enough here, upgrade to a
    lock if fields ever need to change together mid-read.
    """
    backoff = None
    while not stop_event.is_set():
        try:
            result = flush(spool, transport, identity["device_id"], identity["device_token"], send_fn=send_fn)
            backoff = None
            stop_event.wait(0 if result["sent"] else IDLE_POLL_S)
        except TransportAuthError:
            try:
                device_id, device_token = reprovision(cfg, transport, state_path)
                identity["device_id"] = device_id
                identity["device_token"] = device_token
                backoff = None
            except RuntimeError:
                backoff = next_backoff_seconds(backoff)
                stop_event.wait(backoff)
        except TransportRetryableError:
            backoff = next_backoff_seconds(backoff)
            stop_event.wait(backoff)


def capture_supervisor_loop(
    cfg,
    stop_event: threading.Event,
    check_interval_s: float = capture.SUPERVISOR_CHECK_INTERVAL_S,
    start_chain_fn=None,
    health_fn=None,
) -> None:
    """Keep the livemon+catcher chain alive; re-latch to a swapped dongle.

    On any tick where the chain is unhealthy (or never started), run the full
    idempotent restart: kill stale processes, wait for a claimable dongle,
    rescan the frequency, relaunch livemon + catcher. Logs every action.
    """
    livemon, catcher = None, None
    restarts = 0
    while not stop_event.is_set():
        try:
            restarted, livemon, catcher = capture.supervisor_tick(
                cfg, livemon, catcher, start_chain_fn=start_chain_fn, health_fn=health_fn
            )
            if restarted:
                restarts += 1
                capture.supervisor_log(f"chain restarted (total {restarts})")
        except Exception as exc:  # keep the supervisor alive through start failures
            capture.supervisor_log(f"supervisor error: {exc!r}")
        stop_event.wait(check_interval_s)
    capture.supervisor_log("supervisor stopped")


def main() -> None:
    config_path = os.environ.get("SCORPION_CONFIG", DEFAULT_CONFIG_PATH)
    cfg = load_config(config_path=config_path, env=os.environ)

    os.makedirs(cfg.spool_dir, exist_ok=True)
    spool = Spool(os.path.join(cfg.spool_dir, "spool.db"))
    transport = Transport(cfg.server_url)

    device_id, device_token = provision_if_needed(cfg, transport, cfg.state_file)
    identity = {"device_id": device_id, "device_token": device_token}

    def get_fix():
        if not cfg.gnss_enabled:
            return None
        return gnss.get_fix(cfg.gnss_serial, cfg.gnss_baud)

    reader = capture.TailReader(cfg.capture_txt)
    stop_event = threading.Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    threads = [
        threading.Thread(target=heartbeat_loop, args=(transport, identity, cfg.heartbeat_interval_s, stop_event), daemon=True),
        threading.Thread(target=capture_loop, args=(reader, spool, cfg.device_name, get_fix, 3.0, stop_event), daemon=True),
        threading.Thread(target=send_loop, args=(spool, transport, identity, cfg, cfg.state_file, stop_event), daemon=True),
        threading.Thread(target=capture_supervisor_loop, args=(cfg, stop_event), daemon=True),
    ]

    if cfg.presence_enabled:
        presence_spool = Spool(os.path.join(cfg.spool_dir, "presence_spool.db"))
        presence_reader = capture.TailReader(cfg.presence_txt)
        threads += [
            threading.Thread(
                target=presence.run_presence_listener,
                args=(cfg.presence_txt,),
                kwargs={"iface": cfg.presence_iface, "stop_event": stop_event},
                daemon=True,
            ),
            threading.Thread(
                target=presence_capture_loop,
                args=(presence_reader, presence_spool, cfg.device_name, 3.0, stop_event),
                daemon=True,
            ),
            threading.Thread(
                target=send_loop,
                args=(presence_spool, transport, identity, cfg, cfg.state_file, stop_event),
                kwargs={"send_fn": transport.send_presence_events},
                daemon=True,
            ),
        ]

    for t in threads:
        t.start()

    while not stop_event.is_set():
        stop_event.wait(1.0)

    for t in threads:
        t.join(timeout=5.0)


if __name__ == "__main__":
    main()
