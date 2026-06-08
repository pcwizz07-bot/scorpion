#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# IMSI Catcher - One-Click Install
# Anti-Poaching Surveillance Network
#
# Usage:
#   On Proxmox VM:
#     curl -sL https://raw.githubusercontent.com/REPO/main/deploy/install.sh | bash -s server YOUR_GITHUB_USER/imsi-catcher
#
#   On Raspberry Pi (after server is up):
#     curl -sL https://raw.githubusercontent.com/REPO/main/deploy/install.sh | bash -s pi Pi-Name-North LAT LNG ALT SERVER_URL
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════╗"
echo "║      IMSI Catcher - One-Click Install       ║"
echo "║      Anti-Poaching Surveillance Network      ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

MODE="${1:-help}"

case "${MODE}" in
  server)
    # Install on Proxmox VM
    REPO="${2:-yourusername/imsi-catcher}"
    DOMAIN="${3:-localhost}"
    OPENROUTER_KEY="${4:-}"
    
    echo -e "${GREEN}Installing Server (Proxmox VM)...${NC}"
    bash <(curl -sL "https://raw.githubusercontent.com/${REPO}/main/deploy/server-deploy.sh") \
      "${REPO}" "${DOMAIN}" "${OPENROUTER_KEY}"
    ;;

  pi)
    # Install on Raspberry Pi
    PI_NAME="${2:-Pi-$(hostname)}"
    LAT="${3:--1.2921}"
    LNG="${4:-36.8219}"
    ALT="${5:-1800}"
    SERVER="${6:-http://localhost:3000}"
    
    echo -e "${GREEN}Installing Pi Node: ${PI_NAME}...${NC}"
    bash <(curl -sL "https://raw.githubusercontent.com/${REPO:-yourusername/imsi-catcher}/main/deploy/pi-deploy.sh") \
      "${PI_NAME}" "${LAT}" "${LNG}" "${ALT}" "${SERVER}"
    ;;

  help|*)
    echo "Usage:"
    echo ""
    echo "  SERVER (Proxmox VM):"
    echo "    curl -sL https://raw.githubusercontent.com/YOUR_USER/imsi-catcher/main/deploy/install.sh | bash -s server \\"
    echo "      yourusername/imsi-catcher your-domain.com YOUR_OPENROUTER_KEY"
    echo ""
    echo "  PI (Raspberry Pi 3B + RTL-SDR):"
    echo "    curl -sL https://raw.githubusercontent.com/YOUR_USER/imsi-catcher/main/deploy/install.sh | bash -s pi \\"
    echo "      Pi-Name-North -1.2921 36.8219 1800 http://YOUR_SERVER:3000"
    echo ""
    echo "Prerequisites:"
    echo "  Server: Ubuntu/Debian VM with 2GB+ RAM"
    echo "  Pi:    Raspberry Pi 3B + RTL-SDR (RTL2832U) dongle + antenna"
    echo "         8GB+ SD card, Raspbian OS"
    echo ""
    echo "Architecture:"
    echo "  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐"
    echo "  │  Pi-1-North  │     │  Pi-2-East   │     │ Pi-3-South   │"
    echo "  │  RTL-SDR     │     │  RTL-SDR     │     │  RTL-SDR     │"
    echo "  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘"
    echo "         │                    │                    │"
    echo "         └────────────────────┼────────────────────┘"
    echo "                              │"
    echo "                    ┌─────────▼──────────┐"
    echo "                    │  Proxmox VM Server  │"
    echo "                    │  Dashboard + AI     │"
    echo "                    │  Investigator       │"
    echo "                    └────────────────────┘"
    ;;
esac