#!/usr/bin/env bash
set -euo pipefail
# ===== Dungbeetle - Master Install Script =====
MODE="${1:-help}"

case "${MODE}" in
  server)
    echo "=== Installing Dungbeetle Server (VM) ==="
    cd /opt
    git clone https://github.com/pcwizz07-bot/dungbeetle.git 2>/dev/null || true
    cd dungbeetle
    npm install
    npx convex dev --once
    npx convex env set OLLAMA_HOST "http://10.10.20.118:11434" 2>/dev/null || true
    npx convex env set OLLAMA_MODEL "qwen2.5-coder:7b" 2>/dev/null || true

    # Create systemd service for Convex
    sudo tee /etc/systemd/system/dungbeetle-convex.service > /dev/null << 'SVC'
[Unit]
Description=Dungbeetle Convex Backend
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/dungbeetle
ExecStart=/usr/bin/npx convex dev
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
SVC

    # Create systemd service for Dashboard
    sudo tee /etc/systemd/system/dungbeetle-dashboard.service > /dev/null << 'SVC'
[Unit]
Description=Dungbeetle Dashboard
After=dungbeetle-convex.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/dungbeetle
ExecStart=/usr/bin/npx vite --host 0.0.0.0 --port 3000
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
SVC

    sudo systemctl daemon-reload
    sudo systemctl enable --now dungbeetle-convex
    sudo systemctl enable --now dungbeetle-dashboard

    # Install API Proxy for Pi devices
    sudo cp server/api-proxy.py /opt/dungbeetle/api-proxy.py 2>/dev/null || \
      sudo curl -sL "https://raw.githubusercontent.com/pcwizz07-bot/dungbeetle/master/server/api-proxy.py" \
      -o /opt/dungbeetle/api-proxy.py
    sudo tee /etc/systemd/system/dungbeetle-api.service > /dev/null << 'SVC'
[Unit]
Description=Dungbeetle API Proxy
After=network.target
[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /opt/dungbeetle/api-proxy.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
SVC
    sudo systemctl daemon-reload
    sudo systemctl enable --now dungbeetle-api

    echo "=== DONE ==="
    echo "Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
    echo "Convex:    http://127.0.0.1:3210"
    echo "API Proxy: http://$(hostname -I | awk '{print $1}'):3001"
    ;;

  pi)
    PI_NAME="${2:-Pi-$(hostname)}"
    LAT="${3:--25.7461}"
    LNG="${4:-28.1881}"
    SERVER_URL="${5:-http://10.10.20.118:8000}"

    echo "=== Installing Scorpion Pi Node: $PI_NAME ==="

    # Dependencies
    sudo apt-get update -qq
    sudo apt-get install -y -qq git curl python3 python3-pip python3-numpy \
      python3-scipy python3-scapy cmake build-essential libusb-1.0-0-dev \
      librtlsdr-dev rtl-sdr gr-osmosdr jq

    # gr-gsm: pure honest attempt via apt. Not guaranteed available on every
    # distro release; the agent still installs and reports spool status
    # without it, capture just won't produce observations until it's in place.
    if sudo apt-get install -y -qq gr-gsm; then
      echo "gr-gsm installed via apt."
    else
      echo "=========================================================="
      echo "gr-gsm is NOT available via apt on this system."
      echo "Install it manually before GSM capture will work:"
      echo "  - Build from source: https://github.com/ptrkrysik/gr-gsm"
      echo "  - Or run it via Docker: https://hub.docker.com/r/ptrkrysik/gr-gsm"
      echo "Continuing installation; the agent will still run and spool."
      echo "=========================================================="
    fi

    # Clone IMSI scanner
    sudo git clone https://github.com/Oros42/IMSI-catcher.git /opt/dungbeetle-scanner 2>/dev/null || true
    sudo pip3 install importlib scapy --break-system-packages 2>/dev/null || true

    # Blacklist DVB-T
    echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf
    sudo rmmod dvb_usb_rtl28xxu 2>/dev/null || true

    # Install the agent (pi/ package: agent.py + node/) to /opt/scorpion/pi
    sudo mkdir -p /opt/scorpion /etc/scorpion /var/lib/scorpion
    TMP_CLONE="$(mktemp -d)"
    git clone --depth 1 https://github.com/pcwizz07-bot/scorpion.git "$TMP_CLONE" 2>/dev/null || true
    sudo rm -rf /opt/scorpion/pi
    sudo cp -r "$TMP_CLONE/pi" /opt/scorpion/pi
    rm -rf "$TMP_CLONE"
    sudo chmod 700 /var/lib/scorpion

    # Write /etc/scorpion/agent.conf (no secrets in here)
    sudo tee /etc/scorpion/agent.conf > /dev/null << CONF
{
  "device_name": "${PI_NAME}",
  "lat": ${LAT},
  "lng": ${LNG},
  "server_url": "${SERVER_URL}",
  "scan_frequencies_mhz": [947.0, 935.2, 940.0],
  "heartbeat_interval_s": 60,
  "scan_interval_s": 600,
  "spool_dir": "/var/lib/scorpion",
  "state_file": "/var/lib/scorpion/state.json",
  "capture_txt": "/tmp/imsi-output.txt",
  "gnss_enabled": false,
  "gnss_serial": "/dev/ttyUSB2",
  "gnss_baud": 115200
}
CONF
    sudo chmod 600 /etc/scorpion/agent.conf

    # Provisioning token: read from env only, kept out of agent.conf and out
    # of this script's argv/history. Written to a root-only EnvironmentFile
    # so systemd injects it without it appearing in `ps` or shell history.
    if [ -n "${SCORPION_PROVISIONING_TOKEN:-}" ]; then
      sudo tee /etc/scorpion/agent.env > /dev/null << ENVFILE
SCORPION_PROVISIONING_TOKEN=${SCORPION_PROVISIONING_TOKEN}
ENVFILE
      sudo chmod 600 /etc/scorpion/agent.env
    else
      echo "NOTE: SCORPION_PROVISIONING_TOKEN was not set for this run."
      echo "The agent cannot self-provision until you set it:"
      echo "  echo 'SCORPION_PROVISIONING_TOKEN=<token>' | sudo tee /etc/scorpion/agent.env"
      echo "  sudo chmod 600 /etc/scorpion/agent.env && sudo systemctl restart scorpion-pi"
    fi

    # Create systemd service
    sudo tee /etc/systemd/system/scorpion-pi.service > /dev/null << SVC
[Unit]
Description=Scorpion Pi Agent
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/scorpion
ExecStart=/usr/bin/python3 /opt/scorpion/pi/agent.py
Restart=always
RestartSec=30
EnvironmentFile=-/etc/scorpion/agent.env
[Install]
WantedBy=multi-user.target
SVC

    sudo systemctl daemon-reload
    sudo systemctl enable --now scorpion-pi

    echo "=== DONE ==="
    echo "Pi Agent installed: ${PI_NAME}"
    echo "Server: ${SERVER_URL}"
    echo "Check logs: sudo journalctl -u scorpion-pi -f"
    ;;

  *)
    echo "Usage:"
    echo "  Server: sudo bash install.sh server"
    echo "  Pi:     sudo bash install.sh pi Pi-Name lat lng server-url"
    echo ""
    echo "One-liner (pass the provisioning token via env, not argv/history):"
    echo "  export SCORPION_PROVISIONING_TOKEN=<token>"
    echo "  curl -sL https://raw.githubusercontent.com/pcwizz07-bot/scorpion/master/deploy/install.sh \\"
    echo "    | sudo -E bash -s pi Pi-1-North -25.7461 28.1881 http://SERVER:8000"
    echo ""
    echo "Examples:"
    echo "  Server: sudo bash install.sh server"
    echo "  Pi-1:   sudo bash install.sh pi Pi-1-North -25.7461 28.1881 http://10.10.20.118:8000"
    echo "  Pi-2:   sudo bash install.sh pi Pi-2-East -25.7461 28.1881 http://10.10.20.118:8000"
    echo "  Pi-3:   sudo bash install.sh pi Pi-3-South -25.7600 28.2000 http://10.10.20.118:8000"
    ;;
esac