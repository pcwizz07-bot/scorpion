"""grgsm_livemon + simple_IMSI-catcher txt tail reader -> spool; SA freq scan."""
import os
import re
import subprocess
from datetime import datetime, timezone

IMSI_RE = re.compile(r"^\d{5,20}$")
IMSI_CATCHER_PATH = "/opt/dungbeetle-scanner/simple_IMSI-catcher.py"


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


def find_best_frequency(default_frequencies_mhz: list, timeout_s: int = 30) -> float:
    """Run grgsm_scanner over SA bands and return the strongest frequency, else the first default."""
    try:
        result = subprocess.run(
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

    return best_freq if best_freq is not None else default_frequencies_mhz[0]


def start_grgsm_livemon(freq_mhz: float) -> subprocess.Popen:
    return subprocess.Popen(
        ["grgsm_livemon", "-f", f"{freq_mhz}M"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )


def start_imsi_catcher(capture_txt: str) -> subprocess.Popen:
    return subprocess.Popen(
        ["sudo", "python3", IMSI_CATCHER_PATH, "-s", "--txt", capture_txt],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
