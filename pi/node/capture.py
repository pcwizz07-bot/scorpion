"""grgsm_livemon + simple_IMSI-catcher txt tail reader -> spool; SA freq scan."""
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone

IMSI_RE = re.compile(r"^\d{5,20}$")
IMSI_CATCHER_PATH = "/opt/dungbeetle-scanner/simple_IMSI-catcher.py"
LIVEMON_LOG_PATH = "/var/log/scorpion-livemon.log"
CATCHER_LOG_PATH = "/var/log/scorpion-catcher.log"
RTL_POWER_FALLBACK_LOW_MHZ = 935.0
RTL_POWER_FALLBACK_HIGH_MHZ = 960.0
SUPERVISOR_LOG_PATH = "/var/log/scorpion-supervisor.log"
SUPERVISOR_CHECK_INTERVAL_S = 15.0
SUPERVISOR_DONGLE_TIMEOUT_S = 300.0
SUPERVISOR_DONGLE_POLL_S = 5.0
STALE_PROC_MARKERS = ("grgsm_livemon", "simple_IMSI-catcher.py")


def supervisor_log(message: str) -> None:
    """Append an audit line to the supervisor log (root-owned; never DEVNULL)."""
    try:
        with open(SUPERVISOR_LOG_PATH, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {message}\n")
    except OSError:
        pass


def dongle_available(run=subprocess.run, timeout_s: int = 25) -> bool:
    """True when rtl_test can claim a device (i.e. one is present AND not busy)."""
    try:
        result = run(["rtl_test", "-t"], capture_output=True, text=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def wait_for_dongle(
    timeout_s: float = SUPERVISOR_DONGLE_TIMEOUT_S,
    poll_s: float = SUPERVISOR_DONGLE_POLL_S,
    available=None,
    sleep_fn=time.sleep,
) -> bool:
    """Poll until a dongle is claimable or the budget runs out."""
    available_fn = available if available is not None else dongle_available
    waited = 0.0
    while waited < timeout_s:
        if available_fn():
            return True
        sleep_fn(poll_s)
        waited += poll_s
    return available_fn()


def _iter_capture_pids(proc_root: str = "/proc") -> list:
    """Return PIDs whose cmdline matches a capture-chain marker (grgsm_livemon / simple_IMSI-catcher)."""
    found = []
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        cmdline_path = os.path.join(proc_root, entry, "cmdline")
        try:
            with open(cmdline_path, "rb") as f:
                raw = f.read()
        except OSError:
            continue
        text = raw.replace(b"\0", b" ").decode("utf-8", "replace")
        if any(marker in text for marker in STALE_PROC_MARKERS):
            found.append(int(entry))
    return found


def kill_stale_capture_processes(
    proc_root: str = "/proc",
    kill_fn=os.kill,
    sleep_fn=time.sleep,
    poll_after_term_s: float = 0.5,
    own_pid: int | None = None,
) -> list:
    """Terminate orphan capture processes (SIGTERM then SIGKILL), skipping own PID.

    This is the anti-jam cleanup: a leftover grgsm_livemon/IMSI-catcher from a
    manual run (or a previous incarnation) holds the SDR and makes every new
    start fail with 'Failed to open rtlsdr device'. Returns killed PIDs.
    """
    own = os.getpid() if own_pid is None else own_pid
    pids = [pid for pid in _iter_capture_pids(proc_root) if pid != own]
    for pid in pids:
        try:
            kill_fn(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    sleep_fn(poll_after_term_s)
    killed = []
    for pid in pids:
        try:
            kill_fn(pid, signal.SIGKILL)
            killed.append(pid)
        except (OSError, ProcessLookupError):
            pass
    if pids:
        supervisor_log(f"killed stale capture processes: {pids}")
    return killed


def start_capture_chain(cfg, wait_dongle_fn=None, kill_stale_fn=None) -> tuple:
    """Idempotent full chain start: cleanup -> dongle wait -> freq scan -> livemon+catcher.

    Raises RuntimeError if no dongle appears within the timeout. Returns (livemon, catcher).
    """
    stale_fn = kill_stale_fn if kill_stale_fn is not None else kill_stale_capture_processes
    stale_fn()
    wait_fn = wait_dongle_fn if wait_dongle_fn is not None else wait_for_dongle
    if not wait_fn():
        raise RuntimeError(
            "no RTL-SDR dongle claimable after wait; capture chain not started"
        )
    freq = find_best_frequency(cfg.scan_frequencies_mhz)
    supervisor_log(f"starting chain on {freq:.3f} MHz")
    livemon = start_grgsm_livemon(freq)
    time.sleep(2)
    catcher = start_imsi_catcher(cfg.capture_txt)
    return livemon, catcher


def chain_healthy(livemon, catcher) -> bool:
    """Both processes alive (poll() returns None) => chain is up."""
    if livemon is None or catcher is None:
        return False
    return livemon.poll() is None and catcher.poll() is None


def supervisor_tick(
    cfg,
    livemon,
    catcher,
    start_chain_fn=None,
    health_fn=None,
) -> tuple:
    """One supervisor pass: restart the chain if either process died.

    Returns (restarted: bool, livemon, catcher). On restart the returned handles
    are the fresh processes; on a healthy pass they are the unchanged handles.
    """
    health = health_fn if health_fn is not None else chain_healthy
    if health(livemon, catcher):
        return False, livemon, catcher
    supervisor_log("chain unhealthy; restarting")
    start_fn = start_chain_fn if start_chain_fn is not None else start_capture_chain
    new_livemon, new_catcher = start_fn(cfg)
    return True, new_livemon, new_catcher


class TailReader:
    """Tracks inode + offset into a growing text file; resets on truncation/replacement."""

    def __init__(self, path: str):
        self.path = path
        self._inode = None
        self._offset = 0

    def read_new_lines(self) -> list:
        if not os.path.exists(self.path):
            return []
        st = os.stat(self.path)
        if self._inode is not None and st.st_ino != self._inode:
            self._offset = 0
        self._inode = st.st_ino
        if st.st_size < self._offset:
            self._offset = 0

        lines = []
        with open(self.path, "r") as f:
            f.seek(self._offset)
            while True:
                line = f.readline()
                if not line or not line.endswith("\n"):
                    break
                lines.append(line.rstrip("\n"))
                self._offset = f.tell()
        return lines


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line or line.startswith("stamp"):
        return None
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 9:
        return None
    imsi = parts[3].replace(" ", "")
    if not IMSI_RE.match(imsi):
        return None
    return {
        "imsi": imsi,
        # Scanner CSV order: stamp, tmsi1, tmsi2, imsi, country, ...
        "tmsi1": parts[1] or None,
        "tmsi2": parts[2] or None,
        "country": parts[4] or None,
        "brand": parts[5] or None,
        "operator": parts[6] or None,
        "mcc": parts[7] or None,
        "mnc": parts[8] or None,
    }


def capture_new_observations(tail_reader: TailReader, spool, device_name: str, get_fix=None) -> int:
    count = 0
    for raw_line in tail_reader.read_new_lines():
        parsed = parse_line(raw_line)
        if parsed is None:
            continue
        observation = dict(parsed)
        observation["device_name"] = device_name
        observation["observed_at"] = datetime.now(timezone.utc).isoformat()
        if get_fix is not None:
            fix = get_fix()
            if fix is not None:
                observation["lat"] = fix.get("lat")
                observation["lng"] = fix.get("lng")
        spool.append(observation)
        count += 1
    return count


def scan_rtl_power(
    run=subprocess.run,
    low_mhz: float = RTL_POWER_FALLBACK_LOW_MHZ,
    high_mhz: float = RTL_POWER_FALLBACK_HIGH_MHZ,
    step_hz: int = 100_000,
    timeout_s: int = 20,
) -> float | None:
    """Sweep low_mhz-high_mhz with rtl_power and return the strongest bin in MHz, else None.

    Used as a last-resort fallback when grgsm_scanner decodes no cells (energy-only
    environments where GSM framing can't be decoded but a carrier is still present).
    """
    try:
        result = run(
            ["rtl_power", "-f", f"{low_mhz}M:{high_mhz}M:{step_hz}", "-i", str(timeout_s), "-1", "-"],
            capture_output=True,
            text=True,
            timeout=timeout_s + 15,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    best_freq = None
    best_pwr = -1000.0
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            hz_low = float(parts[2])
            hz_step = float(parts[4])
            samples = [float(p) for p in parts[6:] if p]
        except ValueError:
            continue
        for i, pwr in enumerate(samples):
            if pwr > best_pwr:
                best_pwr = pwr
                best_freq = (hz_low + i * hz_step) / 1e6

    return best_freq


def find_best_frequency(default_frequencies_mhz: list, timeout_s: int = 30, run=subprocess.run) -> float:
    """Run grgsm_scanner over SA bands and return the strongest frequency.

    Falls back to an rtl_power energy sweep when the scanner decodes no cells
    (energy-only reception), and finally to the first configured default.
    """
    try:
        result = run(
            ["timeout", str(timeout_s), "grgsm_scanner", "-b", "GSM900"],
            capture_output=True,
            text=True,
            timeout=timeout_s + 15,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
    except (OSError, subprocess.SubprocessError):
        return default_frequencies_mhz[0]

    best_freq = None
    best_pwr = -1000
    for line in result.stdout.splitlines():
        if "Freq:" not in line or "Pwr:" not in line:
            continue
        try:
            freq = float(line.split("Freq:")[1].split(",")[0].strip().rstrip("M"))
            pwr = int(line.split("Pwr:")[1].strip())
        except ValueError:
            continue
        if pwr > best_pwr:
            best_pwr = pwr
            best_freq = freq

    if best_freq is not None:
        return best_freq

    fallback_freq = scan_rtl_power(run=run)
    return fallback_freq if fallback_freq is not None else default_frequencies_mhz[0]


def start_grgsm_livemon(freq_mhz: float, log_path: str = LIVEMON_LOG_PATH) -> subprocess.Popen:
    log_file = open(log_path, "ab")
    return subprocess.Popen(
        ["grgsm_livemon", "-f", f"{freq_mhz}M"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )


def start_imsi_catcher(capture_txt: str, log_path: str = CATCHER_LOG_PATH) -> subprocess.Popen:
    log_file = open(log_path, "ab")
    return subprocess.Popen(
        ["sudo", "python3", IMSI_CATCHER_PATH, "-s", "--txt", capture_txt],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(IMSI_CATCHER_PATH),
    )
