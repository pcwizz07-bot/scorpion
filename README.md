# Dungbeetle 🪲

IMSI surveillance network for anti-poaching. 3x Raspberry Pi 3B + RTL-SDR triangulation, Convex backend, AI investigator via Ollama.

## Architecture

```
Pi-1-North ─┐
Pi-2-East  ─┼──→ VM Server (Convex + Dashboard) ←── You (browser)
Pi-3-South ─┘        │
                     └── Ollama AI (10.10.20.118:11434)
```

## One-Click Install

### Server (Proxmox VM - Ubuntu 24.04)
```bash
curl -sL https://raw.githubusercontent.com/pcwizz07-bot/dungbeetle/master/deploy/install.sh | sudo bash -s server
```
Dashboard at `http://YOUR_VM_IP:3000`

### Pi (Raspberry Pi 3B + RTL-SDR)
```bash
curl -sL https://raw.githubusercontent.com/pcwizz07-bot/dungbeetle/master/deploy/install.sh | sudo bash -s pi \
  Pi-1-North -25.7461 28.1881 http://YOUR_VM_IP:3000
```

## Auto-start Services

**On the VM**, the installer creates:
- `dungbeetle-convex.service` — Convex backend (auto-starts on boot)
- `dungbeetle-dashboard.service` — Dashboard (auto-starts on boot)

**On each Pi**, the installer creates:
- `dungbeetle-pi.service` — Agent that captures IMSIs and sends to server

## South Africa GSM Frequencies

The agent auto-scans common SA frequencies:
- Vodacom/MTN primary: 947.0M, 935.2M, 940.0M
- Cell C: 925.0M, 930.0M
- DCS1800: 1805.0M

## Logs
```bash
# VM
journalctl -u dungbeetle-convex -f
journalctl -u dungbeetle-dashboard -f

# Pi
journalctl -u dungbeetle-pi -f
```