"""LTE cell-presence scanning for the node.

Uses the Evrytania LTE-Cell-Scanner toolchain built at /opt/lte-cell-scanner
(CellSearch binary) plus rtl_power for a quick peak pick. A periodic run:
  - sweeps the band with rtl_power (~25 s) to find the strongest carriers,
  - hunts a focused window around each peak with CellSearch,
  - parses detections (PCI + frequency + RX power) and posts them to
    POST /api/v1/lte/cells using the agent identity.
"""
import json
import re
import subprocess
from pathlib import Path

BIN_DIR = "/opt/lte-cell-scanner/build/src"
CELL_SEARCH = "CellSearch"
RTL_POWER = "rtl_power"
STATE_FILE = "/var/lib/scorpion/state.json"
CONFIG_PATH = "/etc/scorpion/agent.conf"
PEAK_HUNT_BANDWIDTH_MHZ = 0.4  # +/- 0.2 MHz around each peak


_FREQ_RE = re.compile(r"Examining center frequency ([\d.]+) MHz")
_CELL_RE = re.compile(r"cell ID: (\d+)")
_RX_RE = re.compile(r"RX power level: ([-\d.]+) dB")


def parse_cellsearch(stdout: str) -> list[dict]:
    """Parse CellSearch output into [{pci, freq_mhz, signal_raw}] detections."""
    lines = stdout.splitlines()
    cells = []
    current_freq: float | None = None
    for i, line in enumerate(lines):
        m = _FREQ_RE.search(line)
        if m:
            current_freq = float(m.group(1))
            continue
        m = _CELL_RE.search(line)
        if m and current_freq is not None:
            rx = None
            for j in range(i + 1, min(i + 4, len(lines))):
                rm = _RX_RE.search(lines[j])
                if rm:
                    rx = float(rm.group(1))
                    break
            cells.append({"pci": int(m.group(1)), "freq_mhz": current_freq, "signal_raw": rx})
    return cells


def parse_rtl_power(stdout: str, top_n: int = 3) -> list[float]:
    """Return the strongest bin-center frequencies (MHz) from rtl_power CSV."""
    best: dict[float, float] = {}
    for line in stdout.splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 7:
            continue
        try:
            lo = float(p[2])
            step = float(p[4])
            samples = [float(x) for x in p[6:] if x]
        except ValueError:
            continue
        if not samples:
            continue
        mx = max(samples)
        best[lo + step * (samples.index(mx) + 0.5)] = mx
    return [f / 1e6 for f, _ in sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]


def run_rtl_power(low_mhz: float, high_mhz: float, step_hz: int = 200_000, timeout_s: int = 30) -> str:
    result = subprocess.run(
        ["rtl_power", "-f", f"{low_mhz}M:{high_mhz}M:{step_hz}", "-i", str(timeout_s), "-1", "-"],
        capture_output=True,
        text=True,
        timeout=timeout_s + 15,
    )
    return result.stdout


def run_cellsearch(start_mhz: float, end_mhz: float, timeout_s: int = 120) -> str:
    result = subprocess.run(
        [f"{BIN_DIR}/{CELL_SEARCH}", "-s", f"{start_mhz}e6", "-e", f"{end_mhz}e6"],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")


def scan_cells(low_mhz: float = 925.0, high_mhz: float = 947.9) -> list[dict]:
    """Full scan: pick peaks, hunt each, return parsed detections."""
    sweep = run_rtl_power(low_mhz, high_mhz)
    peaks = parse_rtl_power(sweep)
    cells: list[dict] = []
    for peak in peaks:
        lo = max(low_mhz, peak - PEAK_HUNT_BANDWIDTH_MHZ / 2)
        hi = min(high_mhz, peak + PEAK_HUNT_BANDWIDTH_MHZ / 2)
        out = run_cellsearch(lo, hi)
        for cell in parse_cellsearch(out):
            cell["earfcn"] = round((cell["freq_mhz"] - 925.0) * 10 + 3500)
            cell["band"] = 8
            if cell not in cells:
                cells.append(cell)
    return cells


def load_identity(state_file: str = STATE_FILE) -> dict:
    with open(state_file, encoding="utf-8") as f:
        return json.load(f)


def post_cells(cells: list[dict], identity: dict, server_url: str) -> dict:
    """POST detections to the backend via urllib (no extra deps)."""
    import urllib.request

    payload = json.dumps({"cells": cells}).encode()
    req = urllib.request.Request(
        server_url.rstrip("/") + "/api/v1/lte/cells",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Device-Token": identity["device_token"],
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    from pi.node.config import load_config

    cfg = load_config(config_path=CONFIG_PATH)
    cells = scan_cells()
    if not cells:
        return 0
    identity = load_identity()
    result = post_cells(cells, identity, cfg.server_url)
    print(json.dumps({"posted": result, "cells": cells}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())