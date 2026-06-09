#!/usr/bin/env python3
"""
Dungbeetle Pi Agent - IMSI Catcher for Anti-Poaching
Runs on Raspberry Pi 3B + RTL-SDR dongle
Captures GSM IMSIs and sends to central server
"""
import json, time, os, sys, socket, struct, subprocess, threading, urllib.request, urllib.error
from datetime import datetime, timezone
import signal

# ===== CONFIG =====
CONFIG = {
    "device_name": os.environ.get("PI_NAME", "Pi-$(hostname)"),
    "lat": float(os.environ.get("LAT", "-25.7461")),
    "lng": float(os.environ.get("LNG", "28.1881")),
    "server": os.environ.get("SERVER", "http://10.10.20.118:3000"),
    "convex": os.environ.get("CONVEX", "http://10.14.13.250:3210"),
    "gsm_freq": os.environ.get("FREQ", "947.0M"),
    "scan_interval": 600,
    "heartbeat_interval": 60,
}
LOG_FILE = "/var/log/dungbeetle-agent.log"
IMSI_FILE = "/tmp/imsi-output.txt"
PID_FILE = "/var/run/dungbeetle-agent.pid"
device_id = None
running = True

# Known SA frequencies to try (Vodacom, MTN, Cell C, Telkom)
SA_FREQUENCIES = ["947.0M", "935.2M", "940.0M", "942.0M", "945.0M",
                  "950.0M", "925.0M", "930.0M", "955.0M", "960.0M", "1805.0M", "1820.0M"]

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except: pass

def register_device():
    global device_id
    try:
        payload = json.dumps({
            "name": CONFIG["device_name"],
            "lat": CONFIG["lat"],
            "lng": CONFIG["lng"],
            "firmwareVersion": "dungbeetle-v1",
        }).encode()
        req = urllib.request.Request(
            f"{CONFIG['convex']}/api/mutation?functionName=devices:register",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        device_id = data
        log(f"Registered as {CONFIG['device_name']} -> {device_id}")
        return True
    except Exception as e:
        log(f"Registration failed: {e}")
        return False

def send_heartbeat():
    while running:
        if device_id:
            try:
                payload = json.dumps({"deviceId": device_id}).encode()
                req = urllib.request.Request(
                    f"{CONFIG['convex']}/api/mutation?functionName=devices:heartbeat",
                    data=payload, headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=5)
            except: pass
        time.sleep(CONFIG["heartbeat_interval"])

def send_observation(imsi, mcc="", mnc="", country="", brand="", operator="", signal=-75):
    if not device_id:
        return False
    try:
        payload = json.dumps({
            "deviceId": device_id,
            "sensorId": device_id,
            "imsi": imsi.replace(" ", ""),
            "mcc": mcc or "000",
            "mnc": mnc or "00",
            "country": country,
            "brand": brand,
            "operator": operator,
            "signalDbm": signal,
        }).encode()
        req = urllib.request.Request(
            f"{CONFIG['convex']}/api/mutation?functionName=observations:recordObservation",
            data=payload, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        log(f"Send failed: {e}")
        return False

def parse_imsi_file():
    """Watch the IMSI output file for new entries"""
    if not os.path.exists(IMSI_FILE):
        open(IMSI_FILE, "w").close()
    last_size = 0
    while running:
        time.sleep(3)
        try:
            size = os.path.getsize(IMSI_FILE)
            if size < last_size:
                last_size = 0
            if size == last_size:
                continue
            with open(IMSI_FILE, "r") as f:
                f.seek(last_size)
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("stamp"):
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 9:
                        send_observation(parts[3], parts[7], parts[8], parts[4], parts[5], parts[6])
                last_size = f.tell()
        except Exception as e:
            log(f"File parse error: {e}")

def listen_gsmtap():
    """Listen on UDP 4729 for GSMTAP packets from grgsm_livemon"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    try:
        sock.bind(("127.0.0.1", 4729))
    except OSError:
        sock.bind(("127.0.0.1", 4730))
    
    while running:
        try:
            data, addr = sock.recvfrom(4096)
            if len(data) >= 12:
                arfcn = struct.unpack(">H", data[4:6])[0]
                signal = -(data[6] if data[6] < 128 else data[6] - 256)
                log(f"GSM frame ARFCN={arfcn} Signal={signal}dBm")
        except socket.timeout:
            continue
        except Exception as e:
            log(f"GSMTAP error: {e}")

def find_best_frequency():
    """Try common SA frequencies and pick the strongest"""
    log("Scanning for GSM frequencies...")
    try:
        result = subprocess.run(
            ["timeout", "30", "grgsm_scanner", "-b", "GSM900"],
            capture_output=True, text=True, timeout=45,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        )
        for line in result.stdout.split("\n"):
            if "Freq:" in line and "Pwr:" in line:
                freq = line.split("Freq:")[1].strip().split(",")[0]
                pwr_str = line.split("Pwr:")[1].strip()
                try:
                    pwr = int(pwr_str)
                    if pwr > -70:
                        log(f"Found strong signal: {freq} (power: {pwr})")
                        CONFIG["gsm_freq"] = freq
                        return freq
                except: pass
    except: pass
    return CONFIG["gsm_freq"]

def start_grgsm():
    """Start grgsm_livemon in background"""
    freq = find_best_frequency()
    log(f"Starting grgsm_livemon on {freq}...")
    subprocess.Popen(
        ["grgsm_livemon", "-f", freq],
        stdout=open("/dev/null", "w"),
        stderr=subprocess.DEVNULL,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    )

def start_imsi_catcher():
    """Start simple_IMSI-catcher.py saving to file"""
    log("Starting IMSI catcher...")
    subprocess.Popen(
        ["sudo", "python3", "/opt/dungbeetle-scanner/simple_IMSI-catcher.py",
         "-s", "--txt", IMSI_FILE],
        stdout=open("/tmp/imsi-catcher.log", "w"),
        stderr=subprocess.STDOUT,
    )

def cleanup(signum=None, frame=None):
    global running
    running = False
    log("Shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    log(f"Dungbeetle Agent starting: {CONFIG['device_name']}")
    log(f"Server: {CONFIG['server']}")
    
    # Register with server
    for i in range(5):
        if register_device():
            break
        log(f"Retrying registration ({i+1}/5)...")
        time.sleep(5)
    
    # Start background threads
    threading.Thread(target=send_heartbeat, daemon=True).start()
    threading.Thread(target=listen_gsmtap, daemon=True).start()
    threading.Thread(target=parse_imsi_file, daemon=True).start()
    
    # Start GSM capture
    start_grgsm()
    time.sleep(2)
    start_imsi_catcher()
    
    log("Agent ready. Monitoring for IMSIs...")
    
    while running:
        time.sleep(10)