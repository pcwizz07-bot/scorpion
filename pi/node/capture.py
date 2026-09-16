"""grgsm_livemon + simple_IMSI-catcher txt tail reader -> spool; SA freq scan."""
import os
import re
import subprocess
from datetime import datetime, timezone

IMSI_RE = re.compile(r"^\d{5,20}$")
IMSI_CATCHER_PATH = "/opt/dungbeetle-scanner/simple_IMSI-catcher.py"
LIVEMON_LOG_PATH = "/var/log/scorpion-livemon.log"
CATCHER_LOG_PATH = "/var/log/scorpion-catcher.log"
RTL_POWER_FALLBACK_LOW_MHZ = 935.0
RTL_POWER_FALLBACK_HIGH_MHZ = 960.0


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
