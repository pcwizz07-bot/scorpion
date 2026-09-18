"""Supervisor tests: dongle-aware, self-healing capture chain (TDD)."""
import os
import subprocess

import pytest

from pi.node import capture


# ---------- dongle availability ----------

def test_dongle_available_true_when_rtl_test_exits_zero():
    def fake_run(args, **kwargs):
        assert args[0] == "rtl_test"
        return subprocess.CompletedProcess(args, 0, stdout="Found 1 device(s):\n", stderr="")

    assert capture.dongle_available(run=fake_run) is True


def test_dongle_available_false_when_rtl_test_fails():
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="usb_claim_interface error -6\n", stderr="")

    assert capture.dongle_available(run=fake_run) is False


def test_dongle_available_false_when_rtl_test_missing():
    def fake_run(args, **kwargs):
        raise OSError("rtl_test not found")

    assert capture.dongle_available(run=fake_run) is False


# ---------- wait_for_dongle ----------

def test_wait_for_dongle_returns_true_once_available():
    calls = {"n": 0}

    def fake_available():
        calls["n"] += 1
        return calls["n"] >= 3  # unavailable, unavailable, available

    slept = []

    def fake_sleep(s):
        slept.append(s)

    assert capture.wait_for_dongle(timeout_s=30, poll_s=5, available=fake_available, sleep_fn=fake_sleep) is True
    assert len(slept) == 2  # two failed polls before success


def test_wait_for_dongle_returns_false_on_timeout():
    def fake_available():
        return False

    slept = []

    def fake_sleep(s):
        slept.append(s)
        # never available -> bounded by timeout, never sleeping past budget
        assert sum(slept) <= 10 + 5

    assert capture.wait_for_dongle(timeout_s=10, poll_s=5, available=fake_available, sleep_fn=fake_sleep) is False
    assert len(slept) == 2  # sleeps of 5+5 consume the 10s budget


# ---------- stale process cleanup ----------

def _make_proc(tmp_path, pid, cmdline_parts):
    d = tmp_path / str(pid)
    d.mkdir()
    (d / "cmdline").write_bytes(b"\0".join(p.encode() if isinstance(p, str) else p for p in cmdline_parts) + b"\0")
    return d


def test_kill_stale_capture_processes_kills_orphan_chain(tmp_path):
    _make_proc(tmp_path, 111, ["/usr/bin/python3", "/usr/bin/grgsm_livemon", "-f", "944.72M"])
    _make_proc(tmp_path, 222, ["python3", "simple_IMSI-catcher.py", "-s", "--txt", "/tmp/imsi-output.txt"])
    _make_proc(tmp_path, 333, ["/usr/bin/python3", "/opt/scorpion/pi/agent.py"])  # unrelated: leave alone
    _make_proc(tmp_path, 444, ["bash"])  # unrelated

    killed = []
    killed_after_term = set()

    def fake_kill(pid, sig):
        if sig == 9 and pid in (111, 222):
            killed_after_term.add(pid)
        killed.append((pid, sig))

    def fake_sleep(_s):
        return None

    capture.kill_stale_capture_processes(
        proc_root=str(tmp_path), kill_fn=fake_kill, sleep_fn=fake_sleep, poll_after_term_s=0.05
    )

    killed_pids = {pid for pid, _ in killed}
    assert 111 in killed_pids
    assert 222 in killed_pids
    assert 333 not in killed_pids
    assert 444 not in killed_pids


def test_kill_stale_capture_processes_escalates_to_sigkill(tmp_path):
    _make_proc(tmp_path, 555, ["python3", "simple_IMSI-catcher.py", "-s"])

    sigs = []

    def fake_kill(pid, sig):
        sigs.append(sig)  # SIGTERM first, then SIGKILL on retry

    def fake_sleep(_s):
        return None

    capture.kill_stale_capture_processes(
        proc_root=str(tmp_path), kill_fn=fake_kill, sleep_fn=fake_sleep, poll_after_term_s=0.0
    )

    assert sigs[:2] == [15, 9]  # SIGTERM then SIGKILL


def test_kill_stale_capture_processes_skips_own_pid(tmp_path):
    _make_proc(tmp_path, 777, ["python3", "simple_IMSI-catcher.py"])

    killed = []

    def fake_kill(pid, sig):
        killed.append(pid)

    capture.kill_stale_capture_processes(
        proc_root=str(tmp_path), kill_fn=fake_kill, sleep_fn=lambda _s: None, own_pid=777
    )

    assert killed == []


# ---------- supervisor restart logic ----------

def test_supervisor_restarts_chain_when_livemon_dies(monkeypatch):
    calls = {"starts": 0}

    def fake_popen(args, **kwargs):
        calls["starts"] += 1
        if args[0] == "grgsm_livemon":
            return None  # not used by supervisor, only health checks matter
        return None

    dead_livemon = type("P", (), {"poll": lambda self: 0})()  # exited
    alive_catcher = type("P", (), {"poll": lambda self: None})()  # still running

    def fake_start(cfg):
        calls["starts"] += 1
        return dead_livemon, alive_catcher

    monkeypatch.setattr(capture, "start_grgsm_livemon", lambda *a, **k: dead_livemon)
    monkeypatch.setattr(capture, "start_imsi_catcher", lambda *a, **k: alive_catcher)

    # first probe: livemon already exited -> restart -> second probe healthy
    probes = [0, None]

    def fake_chain_health(livemon, catcher):
        return probes.pop(0) is None

    # Simulate one supervisor tick returning True (restarted) then stop
    restarted, new_livemon, new_catcher = capture.supervisor_tick(
        cfg=type("C", (), {"capture_txt": "/tmp/x.txt"})(),
        livemon=dead_livemon,
        catcher=alive_catcher,
        start_chain_fn=fake_start,
        health_fn=fake_chain_health,
    )
    assert restarted is True
    assert calls["starts"] == 1
    assert new_livemon is dead_livemon and new_catcher is alive_catcher


def test_supervisor_tick_no_restart_when_healthy(monkeypatch):
    alive_livemon = type("P", (), {"poll": lambda self: None})()
    alive_catcher = type("P", (), {"poll": lambda self: None})()

    started = []

    def fake_start(cfg):
        started.append(cfg)
        return alive_livemon, alive_catcher

    restarted, l2, c2 = capture.supervisor_tick(
        cfg=type("C", (), {"capture_txt": "/tmp/x.txt"})(),
        livemon=alive_livemon,
        catcher=alive_catcher,
        start_chain_fn=fake_start,
        health_fn=lambda l, c: True,
    )
    assert restarted is False
    assert started == []
    assert l2 is alive_livemon and c2 is alive_catcher


def test_supervisor_tick_restarts_when_catcher_dead(monkeypatch):
    alive_livemon = type("P", (), {"poll": lambda self: None})()
    dead_catcher = type("P", (), {"poll": lambda self: 1})()

    starts = []

    def fake_start(cfg):
        starts.append(True)
        return alive_livemon, alive_catcher2

    alive_catcher2 = type("P", (), {"poll": lambda self: None})()

    restarted, l2, c2 = capture.supervisor_tick(
        cfg=type("C", (), {"capture_txt": "/tmp/x.txt"})(),
        livemon=alive_livemon,
        catcher=dead_catcher,
        start_chain_fn=fake_start,
        health_fn=lambda l, c: c.poll() is None,
    )
    assert restarted is True
    assert len(starts) == 1