# IMSI Catcher - Anti-Poaching Surveillance Network

A distributed IMSI (International Mobile Subscriber Identity) detection system using **3 Raspberry Pi 3B** devices with **RTL-SDR (RTL2832U)** dongles for triangulation and tracking on wildlife reserves. Detected IMSI data flows to a central dashboard with an **AI-powered intelligence analyst**.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Pi-1-North  │     │  Pi-2-East   │     │ Pi-3-South   │
│  RTL-SDR     │     │  RTL-SDR     │     │  RTL-SDR     │
│  IMSI Agent  │     │  IMSI Agent  │     │  IMSI Agent  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │ HTTP/WebSocket
                    ┌───────▼──────────┐
                    │ Proxmox VM       │
                    │ ───────────────  │
                    │ Dashboard (React)│
                    │ Convex Backend   │
                    │ AI Investigator  │
                    │ (OpenRouter/GPT) │
                    └──────────────────┘
```

## One-Click Install

### Prerequisites

**Server (Proxmox VM)**:
- Ubuntu/Debian VM (2GB+ RAM, 20GB disk)
- Ports 80/443 accessible

**Per Raspberry Pi**:
- Raspberry Pi 3B (or better)
- RTL-SDR (RTL2832U) USB dongle + antenna
- 16GB+ SD card with Raspberry Pi OS Lite
- Power supply (battery pack recommended for field use)

### Install Server

```bash
curl -sL https://raw.githubusercontent.com/YOUR_USER/imsi-catcher/main/deploy/install.sh | bash -s server \
  YOUR_GITHUB_USER/imsi-catcher your-domain.com YOUR_OPENROUTER_API_KEY
```

### Install Pi Devices (after server is deployed)

On each Raspberry Pi:

```bash
curl -sL https://raw.githubusercontent.com/YOUR_USER/imsi-catcher/main/deploy/install.sh | bash -s pi \
  Pi-1-North -1.2921 36.8219 1800 http://YOUR_SERVER:3000
```

### Configuration Options

| Pi Parameter | Description | Example |
|-------------|-------------|---------|
| Pi-Name | Unique device name | `Pi-1-North` |
| LAT | Latitude | `-1.2921` |
| LNG | Longitude | `36.8219` |
| ALT | Altitude (meters) | `1800` |
| SERVER_URL | Server URL | `http://192.168.1.100:3000` |

## Features

### 📡 IMSI Detection
Captures IMSI, TMSI, MCC, MNC from GSM paging messages using `grgsm_livemon` + custom parser

### 📍 Triangulation
Uses signal strength from 3+ Pi devices to estimate phone positions with confidence scoring

### 🤖 AI Intelligence Analyst
- Analyzes movement patterns across the reserve
- Flags suspicious IMSIs and unusual activity
- Generates actionable intelligence reports
- Correlates sightings across all devices
- Powered by OpenRouter (GPT-4o-mini or any model)

### 📊 Dashboard
- Real-time IMSI feed
- Deployment map with device status
- Alert management
- Device health monitoring

## Manual Setup

### Server
```bash
git clone https://github.com/YOUR_USER/imsi-catcher.git
cd imsi-catcher
npm install
npx convex dev --once
npx convex env set OPENROUTER_API_KEY your_key
npm run dev
```

### Pi (Manual)
```bash
sudo apt install python3-numpy python3-scipy python3-scapy gr-gsm rtl-sdr
git clone https://github.com/Oros42/IMSI-catcher.git
cd IMSI-catcher

# Find GSM frequencies
grgsm_scanner

# Terminal 1 - Live monitor
grgsm_livemon -f 925.4M

# Terminal 2 - IMSI capture
sudo python3 simple_IMSI-catcher.py -s
```

## Scripts

```
deploy/
├── install.sh          # One-click installer (server or pi)
├── server-deploy.sh    # Proxmox VM deployment
└── pi-deploy.sh        # Raspberry Pi deployment
server/
└── api-server.mjs      # HTTP API for device communication
```

## Tech Stack

- **Frontend**: TanStack Start (React), Tailwind CSS v4
- **Backend**: Convex (real-time database, server functions)
- **AI**: @convex-dev/agent + OpenRouter (@openrouter/ai-sdk-provider)
- **SDR**: RTL-SDR (RTL2832U) + gr-gsm
- **Deployment**: Systemd services, Nginx, Docker-ready

## Credits

- [Oros42/IMSI-catcher](https://github.com/Oros42/IMSI-catcher) - Original IMSI detection engine
- Osmocom & gr-gsm community - GSM decoding libraries
- RTL-SDR project - Affordable SDR hardware

## License

MIT - Built for wildlife conservation and anti-poaching efforts.