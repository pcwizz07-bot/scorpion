#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# IMSI Catcher - Proxmox VM One-Click Deploy
# Central Server + Dashboard
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════╗"
echo "║   IMSI Catcher - Proxmox VM Server Deploy   ║"
echo "║       Anti-Poaching Surveillance Hub         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
GITHUB_REPO="${1:-yourusername/imsi-catcher}"
DOMAIN="${2:-localhost}"
OPENROUTER_KEY="${3:-}"
ADMIN_EMAIL="${4:-admin@reserve.org}"

echo "Repo: ${GITHUB_REPO}"
echo "Domain: ${DOMAIN}"
echo ""

# Install Node.js and dependencies
echo -e "${YELLOW}[1/6] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq \
    curl wget git \
    nginx certbot python3-certbot-nginx \
    ufw fail2ban \
    redis-server \
    postgresql postgresql-contrib \
    nodejs npm \
    build-essential

# Install Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Step 2: Clone and build
echo -e "${YELLOW}[2/6] Cloning and building application...${NC}"
cd /opt
git clone "https://github.com/${GITHUB_REPO}.git" imsi-catcher 2>/dev/null || {
    echo -e "${YELLOW}Creating fresh project...${NC}"
    mkdir -p imsi-catcher
}
cd imsi-catcher

# Install dependencies
npm install

# Build the application
npm run build 2>/dev/null || {
    echo -e "${YELLOW}Building with vite...${NC}"
    npx vite build
}

# Step 3: Configure Convex
echo -e "${YELLOW}[3/6] Setting up Convex backend...${NC}"
cd /opt/imsi-catcher

# Initialize Convex project
npx convex dev --once 2>/dev/null || true

# Set OpenRouter API key if provided
if [ -n "${OPENROUTER_KEY}" ]; then
    npx convex env set OPENROUTER_API_KEY "${OPENROUTER_KEY}"
    echo -e "${GREEN}✓ OpenRouter API key configured${NC}"
else
    echo -e "${YELLOW}⚠ No OpenRouter key. AI investigator will not work.${NC}"
    echo "  Get one at: https://openrouter.ai/keys"
    echo "  Set later: npx convex env set OPENROUTER_API_KEY <key>"
fi

# Step 4: Configure Nginx
echo -e "${YELLOW}[4/6] Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/imsi-catcher << 'NGINX'
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Dashboard static files
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    # Convex backend proxying
    location /api/ {
        proxy_pass http://127.0.0.1:3210/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API endpoints for Pi devices
    location /api/devices/ {
        proxy_pass http://127.0.0.1:3001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/observations/ {
        proxy_pass http://127.0.0.1:3001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Static assets
    location /assets/ {
        alias /opt/imsi-catcher/dist/assets/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    # SSL will be configured by certbot
    include /etc/nginx/snippets/imsi-catcher-ssl.conf;
}
NGINX

ln -sf /etc/nginx/sites-available/imsi-catcher /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Step 5: Setup firewall and security
echo -e "${YELLOW}[5/6] Configuring security...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw allow 3210/tcp
ufw --force enable

# Configure fail2ban
cat > /etc/fail2ban/jail.local << 'FAIL2BAN'
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600

[imsi-catcher]
enabled = true
port = 80,443
maxretry = 10
bantime = 3600
FAIL2BAN

systemctl restart fail2ban

# Step 6: Create systemd service
echo -e "${YELLOW}[6/6] Creating systemd services...${NC}"

# Dashboard service
cat > /etc/systemd/system/imsi-dashboard.service << 'DASHSVC'
[Unit]
Description=IMSI Catcher Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/imsi-catcher
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=HOST=0.0.0.0
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
DASHSVC

# HTTP API service for Pi devices
cat > /etc/systemd/system/imsi-api.service << 'APISVC'
[Unit]
Description=IMSI Catcher HTTP API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/imsi-catcher
ExecStart=/usr/bin/node server/api-server.mjs 2>/dev/null || echo "API server placeholder"
Restart=always
RestartSec=10
Environment=PORT=3001

[Install]
WantedBy=multi-user.target
APISVC

systemctl daemon-reload
systemctl enable imsi-dashboard
systemctl enable imsi-api

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Proxmox VM Deployment Complete!      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "Services:"
echo "  Dashboard:        http://${DOMAIN}:3000"
echo "  Convex Backend:   http://${DOMAIN}:3210"
echo ""
echo "Management:"
echo "  Start dashboard:  systemctl start imsi-dashboard"
echo "  View logs:        journalctl -u imsi-dashboard -f"
echo "  Restart:          systemctl restart imsi-dashboard"
echo ""
echo "Next - Deploy Pis:"
echo '  curl -sL https://raw.githubusercontent.com/REPO/main/deploy/pi-deploy.sh | bash -s Pi-Name lat lng altitude http://SERVER:3000'
echo ""
echo -e "${YELLOW}Don't forget to:${NC}"
echo "  1. Set up SSL: certbot --nginx -d ${DOMAIN}"
echo "  2. Configure OpenRouter key for AI investigator"
echo "  3. Deploy the 3 Raspberry Pis"