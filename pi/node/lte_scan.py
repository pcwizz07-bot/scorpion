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
import sys
from pathlib import Path

BIN_DIR = "/opt/lte-cell-scanner/build/src"
CELL_SEARCH = "CellSearch"
RTL_POWER = "rtl_power"
STATE_FILE = "/var/lib/scorpion/state.json"
CONFIG_PATH = "/etc/scorpion/agent.conf"
PEAK_HUNT_BANDWIDTH_MHZ = 0.3  # +/- 0.15 MHz around each peak
PEAK_HUNT_TIMEOUT_S = 180


_FREQ_RE = re.compile(r"Examining center frequency ([\d.]+) MHz")
_CELL_RE = re.compile(r"cell ID: (\d+)")
_RX_RE = re.compile(r"RX power level: ([-\d.]+) dB")

# LTE downlink bands reachable by the R820T2 dongle (24-1766 MHz).
# (band, dl_low_mhz, dl_high_mhz, earfcn_low)
LTE_BANDS = [
    (8, 925.0, 960.0, 3450),    # LTE900
    (3, 1805.0, 1880.0, 1200),  # DCS1800 (V3 dongle reaches 1766; partial coverage)
]


def band_and_earfcn(freq_mhz: float) -> tuple[int | None, int | None]:
    """Map a downlink frequency to (band, earfcn) using the configured LTE bands."""
    for band, low, high, earfcn_low in LTE_BANDS:
        if low <= freq_mhz <= high:
            return band, round((freq_mhz - low) * 10 + earfcn_low)
    return None, None


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


def parse_rtl_power(stdout: str, top_n: int = 5) -> list[tuple[float, float]]:
    """Return the strongest bin centers as [(freq_mhz, dbm)] from rtl_power CSV."""
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
    return [(f / 1e6, pwr) for f, pwr in sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]


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


def scan_cells(bands: list[tuple[int, float, float, int]] | None = None) -> list[dict]:
    """Scan each reachable LTE band: pick peaks, hunt each, collect detections.

    A slow/stuck hunt on one peak must never kill the whole run — it is
    logged and skipped so the remaining peaks still get scanned.
    """
    bands = bands or [b for b in LTE_BANDS if b[2] <= 1766.0]  # R820T2 reach
    cells: list[dict] = []
    for band, low_mhz, high_mhz, _earfcn_low in bands:
        sweep = run_rtl_power(low_mhz, high_mhz)
        peaks = parse_rtl_power(sweep, top_n=2)
        for peak, _pwr in peaks:
            lo = max(low_mhz, peak - PEAK_HUNT_BANDWIDTH_MHZ / 2)
            hi = min(high_mhz, peak + PEAK_HUNT_BANDWIDTH_MHZ / 2)
            try:
                out = run_cellsearch(lo, hi, timeout_s=PEAK_HUNT_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                print(f"hunt at {peak:.3f} MHz timed out; skipping", file=sys.stderr)
                continue
            except subprocess.SubprocessError as exc:
                print(f"hunt at {peak:.3f} MHz failed: {exc!r}", file=sys.stderr)
                continue
            for cell in parse_cellsearch(out):
                cell_band, earfcn = band_and_earfcn(cell["freq_mhz"])
                cell["earfcn"] = earfcn
                cell["band"] = cell_band
                if cell["signal_raw"] is not None:
                    cell["signal_dbm"] = int(round(cell["signal_raw"]))
                cell.pop("signal_raw", None)
                if cell not in cells:
                    cells.append(cell)
    return cells


def scan_energy(bands: list[tuple[int, float, float, int]] | None = None, top_n: int = 5) -> list[dict]:
    """Energy-only cell presence: rtl_power peaks per band, no PCI decode.

    Reliable on any working dongle — carrier frequency + power only. This is
    the demo-suitable mode when coherent decode (CellSearch) is unreliable.
    """
    bands = bands or [b for b in LTE_BANDS if b[2] <= 1766.0]
    cells: list[dict] = []
    for band, low_mhz, high_mhz, _earfcn_low in bands:
        sweep = run_rtl_power(low_mhz, high_mhz)
        for peak_mhz, dbm in parse_rtl_power(sweep, top_n=top_n):
            cell_band, earfcn = band_and_earfcn(peak_mhz)
            cells.append(
                {
                    "pci": None,  # energy-only: no PCI identity
                    "freq_mhz": peak_mhz,
                    "signal_dbm": int(round(dbm)),
                    "band": cell_band,
                    "earfcn": earfcn,
                }
            )
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

    energy_only = "--energy" in sys.argv
    try:
        cfg = load_config(config_path=CONFIG_PATH)
        cells = scan_energy() if energy_only else scan_cells()
        if not cells:
            return 0
        identity = load_identity()
        result = post_cells(cells, identity, cfg.server_url)
        print(json.dumps({"posted": result, "cells": cells}))
    except Exception as exc:  # never crash the wrapper: log and exit clean
        print(f"lte scan error: {exc!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())