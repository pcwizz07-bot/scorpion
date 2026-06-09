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

    echo "=== DONE ==="
    echo "Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
    echo "Convex:    http://127.0.0.1:3210"
    ;;

  pi)
    PI_NAME="${2:-Pi-$(hostname)}"
    LAT="${3:--25.7461}"
    LNG="${4:-28.1881}"
    SERVER="${5:-http://10.10.20.118:3000}"

    echo "=== Installing Dungbeetle Pi Node: $PI_NAME ==="

    # Dependencies
    sudo apt-get update -qq
    sudo apt-get install -y -qq git curl python3 python3-pip python3-numpy \
      python3-scipy python3-scapy cmake build-essential libusb-1.0-0-dev \
      librtlsdr-dev rtl-sdr gr-osmosdr gr-gsm jq

    # Clone IMSI scanner
    sudo git clone https://github.com/Oros42/IMSI-catcher.git /opt/dungbeetle-scanner 2>/dev/null || true
    sudo pip3 install importlib scapy --break-system-packages 2>/dev/null || true

    # Blacklist DVB-T
    echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf
    sudo rmmod dvb_usb_rtl28xxu 2>/dev/null || true

    # Download the agent script
    sudo mkdir -p /opt/dungbeetle /var/log
    sudo curl -sL "https://raw.githubusercontent.com/pcwizz07-bot/dungbeetle/master/pi/agent.py" \
      -o /opt/dungbeetle/agent.py
    sudo chmod +x /opt/dungbeetle/agent.py

    # Create systemd service
    sudo tee /etc/systemd/system/dungbeetle-pi.service > /dev/null << SVC
[Unit]
Description=Dungbeetle Pi Agent
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/dungbeetle
ExecStart=/usr/bin/python3 /opt/dungbeetle/agent.py
Restart=always
RestartSec=30
Environment=PI_NAME=${PI_NAME}
Environment=LAT=${LAT}
Environment=LNG=${LNG}
Environment=SERVER=${SERVER}
[Install]
WantedBy=multi-user.target
SVC

    sudo systemctl daemon-reload
    sudo systemctl enable --now dungbeetle-pi

    echo "=== DONE ==="
    echo "Pi Agent installed: ${PI_NAME}"
    echo "Server: ${SERVER}"
    echo "Check logs: sudo journalctl -u dungbeetle-pi -f"
    ;;

  *)
    echo "Usage:"
    echo "  Server: sudo bash install.sh server"
    echo "  Pi:     sudo bash install.sh pi Pi-Name lat lng server-url"
    echo ""
    echo "Examples:"
    echo "  Server: sudo bash install.sh server"
    echo "  Pi-1:   sudo bash install.sh pi Pi-1-North -25.7461 28.1881 http://10.10.20.118:3000"
    echo "  Pi-2:   sudo bash install.sh pi Pi-2-East -25.7461 28.1881 http://10.10.20.118:3000"
    echo "  Pi-3:   sudo bash install.sh pi Pi-3-South -25.7600 28.2000 http://10.10.20.118:3000"
    ;;
esac