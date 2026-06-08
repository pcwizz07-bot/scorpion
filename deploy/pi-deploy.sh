#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# IMSI Catcher - Raspberry Pi Deployment Script
# For 3x Pi 3B + RTL-SDR DVB-T dongles
# Anti-Poaching Surveillance Network
# ============================================================

# Configuration - EDIT THESE
DEVICE_NAME="${1:-Pi-$(hostname)}"
LAT="${2:--1.2921}"      # Default: reserve coordinates
LNG="${3:-36.8219}"       # Replace with actual coordinates
ALTITUDE="${4:-1800}"     # Altitude in meters
SERVER_URL="${5:-http://your-server:3000}"  # Your Proxmox VM server URL
CONVEX_URL=""  # Leave empty for auto-config

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'


echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════╗"
echo "║     IMSI Catcher - Pi Deployment Script     ║"
echo "║     Anti-Poaching Surveillance Network      ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Device: ${DEVICE_NAME}"
echo "Location: ${LAT}, ${LNG} (alt: ${ALTITUDE}m)"
echo "Server: ${SERVER_URL}"
echo ""

# Step 1: System update & dependencies
echo -e "${YELLOW}[1/7] Installing system dependencies...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    git curl wget \
    python3 python3-pip python3-numpy python3-scipy \
    python3-scapy python3-serial \
    cmake build-essential libusb-1.0-0-dev \
    librtlsdr-dev rtl-sdr \
    gr-osmosdr gr-gsm \
    sqlite3 jq \
    nmap netcat-openbsd \
    nodejs npm \
    --no-install-recommends

# Step 2: Install IMSI-catcher
echo -e "${YELLOW}[2/7] Installing IMSI-catcher...${NC}"
cd /opt
sudo git clone https://github.com/Oros42/IMSI-catcher.git /opt/imsi-catcher 2>/dev/null || true
cd /opt/imsi-catcher
sudo pip3 install -q importlib scapy 2>/dev/null || true

# Step 3: Install RTL-SDR drivers
echo -e "${YELLOW}[3/7] Configuring RTL-SDR...${NC}"
# Blacklist default DVB-T drivers
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf
sudo rmmod dvb_usb_rtl28xxu 2>/dev/null || true

# Test SDR
echo -e "${YELLOW}Testing RTL-SDR...${NC}"
rtl_test -t 2>&1 | head -5 || {
    echo -e "${RED}RTL-SDR not detected! Check USB connection.${NC}"
    echo "Continuing anyway..."
}

# Step 4: Install agent software
echo -e "${YELLOW}[4/7] Installing IMSI Catcher Agent...${NC}"
sudo mkdir -p /opt/imsi-agent
cat > /tmp/agent.py << 'AGENTPY'
#!/usr/bin/env python3
"""
IMSI Catcher Agent for Raspberry Pi
Sends observed IMSI data to the central server
"""
import json
import socket
import struct
import time
import os
import sys
import subprocess
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone

CONFIG = {
    "device_name": os.environ.get("DEVICE_NAME", "Pi-Unknown"),
    "lat": float(os.environ.get("LAT", "-1.2921")),
    "lng": float(os.environ.get("LNG", "36.8219")),
    "altitude": int(os.environ.get("ALTITUDE", "1800")),
    "server_url": os.environ.get("SERVER_URL", "http://localhost:3000"),
    "convex_url": os.environ.get("CONVEX_URL", ""),
    "heartbeat_interval": 60,
    "scan_interval": 300,
}


def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] {msg}", flush=True)


def register_device():
    """Register this Pi with the central server"""
    payload = {
        "name": CONFIG["device_name"],
        "lat": CONFIG["lat"],
        "lng": CONFIG["lng"],
        "altitude": CONFIG["altitude"],
        "firmware_version": "1.0.0-pi3b",
    }
    try:
        req = urllib.request.Request(
            f"{CONFIG['server_url']}/api/devices/register",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        CONFIG["device_id"] = data.get("deviceId", "")
        log(f"Registered: {CONFIG['device_name']} -> {CONFIG['device_id']}")
        return True
    except Exception as e:
        log(f"Registration failed: {e}")
        return False


def heartbeat():
    """Send heartbeat to server"""
    while True:
        try:
            if CONFIG.get("device_id"):
                payload = {"deviceId": CONFIG["device_id"]}
                req = urllib.request.Request(
                    f"{CONFIG['server_url']}/api/devices/heartbeat",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
        time.sleep(CONFIG["heartbeat_interval"])


def scan_gsm():
    """Run GSM scan and livemon in background"""
    while True:
        log("Starting GSM scan...")
        try:
            # Scan for GSM base stations
            subprocess.run(
                ["timeout", "60", "grgsm_scanner", "-j"],
                capture_output=True,
                timeout=120,
            )
        except Exception as e:
            log(f"Scan error: {e}")
        time.sleep(CONFIG["scan_interval"])


def main():
    log(f"Starting IMSI Agent: {CONFIG['device_name']}")
    
    # Register with server
    register_device()
    
    # Start background threads
    threading.Thread(target=heartbeat, daemon=True).start()
    threading.Thread(target=scan_gsm, daemon=True).start()
    
    # Listen for GSM data from grgsm_livemon
    log("Listening on UDP port 4729 for GSM data...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    
    try:
        sock.bind(("127.0.0.1", 4729))
    except OSError:
        sock.bind(("127.0.0.1", 4730))
    
    log("Agent ready. Waiting for GSM data...")
    
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            # Extract GSMTAP header to get signal info
            if len(data) >= 12:
                version = data[0]
                hdr_len = data[1]
                pkt_type = data[2]
                timeslot = data[3]
                arfcn = struct.unpack(">H", data[4:6])[0]
                signal_dbm = -data[6] if data[6] < 128 else data[6] - 256
                
                log(f"GSM frame: ARFCN={arfcn} Signal={signal_dbm}dBm")
                
                # Send to server
                try:
                    payload = json.dumps({
                        "deviceId": CONFIG.get("device_id", ""),
                        "arfcn": arfcn,
                        "signalDbm": signal_dbm,
                        "timestamp": int(time.time() * 1000),
                    }).encode()
                    
                    for endpoint in ["/api/observations/raw", "/api/gsm/frame"]:
                        try:
                            req = urllib.request.Request(
                                f"{CONFIG['server_url']}{endpoint}",
                                data=payload,
                                headers={"Content-Type": "application/json"},
                                method="POST",
                            )
                            urllib.request.urlopen(req, timeout=3)
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
                    
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            log("Shutting down...")
            break
        except Exception as e:
            log(f"Error: {e}")


if __name__ == "__main__":
    main()
AGENTPY

sudo cp /tmp/agent.py /opt/imsi-agent/agent.py
sudo chmod +x /opt/imsi-agent/agent.py

# Step 5: Create systemd service
echo -e "${YELLOW}[5/7] Creating systemd service...${NC}"
cat > /tmp/imsi-agent.service << 'SERVICE'
[Unit]
Description=IMSI Catcher Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/imsi-agent
ExecStart=/usr/bin/python3 /opt/imsi-agent/agent.py
Restart=always
RestartSec=30
Environment=DEVICE_NAME=%I
Environment=SERVER_URL=http://SERVER_PLACEHOLDER:3000
Environment=LAT=0.0
Environment=LNG=0.0
Environment=ALTITUDE=0

[Install]
WantedBy=multi-user.target
SERVICE

sudo cp /tmp/imsi-agent.service /etc/systemd/system/imsi-agent.service

# Step 6: Create the livemon runner
echo -e "${YELLOW}[6/7] Creating GSM livemon scripts...${NC}"
cat > /opt/imsi-agent/start-livemon.sh << 'LIVEMON'
#!/usr/bin/env bash
# Start the GSM live monitor and pipe to agent
echo "Starting grgsm_livemon..."
while true; do
    grgsm_livemon -f 925.4M 2>&1 | tee -a /var/log/imsi-gsm.log
    sleep 2
done
LIVEMON
chmod +x /opt/imsi-agent/start-livemon.sh

cat > /opt/imsi-agent/start-scanner.sh << 'SCANNER'
#!/usr/bin/env bash
# Scan for GSM frequencies and save results
while true; do
    echo "Scanning GSM frequencies..."
    grgsm_scanner -j > /tmp/gsm-bands.json 2>/dev/null
    if [ -f /tmp/gsm-bands.json ]; then
        cat /tmp/gsm-bands.json | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data:
        # Use the strongest frequency
        best = max(data, key=lambda x: x.get('power', 0))
        freq = best.get('frequency', '925.4M')
        print(f'Best frequency: {freq}')
except:
    pass
" 2>/dev/null
    fi
    sleep 300
done
SCANNER
chmod +x /opt/imsi-agent/start-scanner.sh

# Step 7: Create start script and enable service
echo -e "${YELLOW}[7/7] Finalizing...${NC}"

# Create convenience start script
cat > /opt/imsi-agent/run.sh << 'RUNSH'
#!/usr/bin/env bash
set -e
# Run all IMSI catcher components
echo "Starting IMSI Catcher components..."

# 1. Start the GSM live monitor in background
/opt/imsi-agent/start-livemon.sh &
LIVEMON_PID=$!

# 2. Start the scanner in background
/opt/imsi-agent/start-scanner.sh &
SCANNER_PID=$!

# 3. Start the agent
echo "Starting IMSI Agent..."
python3 /opt/imsi-agent/agent.py

# Cleanup
kill $LIVEMON_PID $SCANNER_PID 2>/dev/null
RUNSH
chmod +x /opt/imsi-agent/run.sh

# Update the service with actual config
sudo sed -i "s/DEVICE_NAME=%I/DEVICE_NAME=${DEVICE_NAME}/" /etc/systemd/system/imsi-agent.service
sudo sed -i "s|SERVER_URL=http://SERVER_PLACEHOLDER:3000|SERVER_URL=${SERVER_URL}|" /etc/systemd/system/imsi-agent.service
sudo sed -i "s/LAT=0.0/LAT=${LAT}/" /etc/systemd/system/imsi-agent.service
sudo sed -i "s/LNG=0.0/LNG=${LNG}/" /etc/systemd/system/imsi-agent.service
sudo sed -i "s/ALTITUDE=0/ALTITUDE=${ALTITUDE}/" /etc/systemd/system/imsi-agent.service

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable imsi-agent.service
sudo systemctl restart imsi-agent.service || true

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Deployment Complete!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Device: ${BLUE}${DEVICE_NAME}${NC}"
echo -e "Location: ${BLUE}${LAT}, ${LNG}${NC}"
echo -e "Server: ${BLUE}${SERVER_URL}${NC}"
echo ""
echo "Next steps:"
echo "  1. Start the GSM live monitor:     sudo systemctl start imsi-agent"
echo "  2. Run the full stack:              /opt/imsi-agent/run.sh"
echo "  3. Check logs:                      journalctl -u imsi-agent -f"
echo "  4. Scan for GSM frequencies:        grgsm_scanner"
echo "  5. Test IMSI capture:               sudo python3 /opt/imsi-catcher/simple_IMSI-catcher.py -s"
echo ""
echo "In a separate terminal, run: grgsm_livemon -f <FREQUENCY>"
echo "Find frequencies with: grgsm_scanner"