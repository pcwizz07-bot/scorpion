#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# IMSI Catcher - GitHub Upload & Setup
# Creates the repo and pushes everything to GitHub
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}IMSI Catcher - GitHub Repo Setup${NC}"
echo ""

# Ask for GitHub username
read -p "GitHub username: " GITHUB_USER
read -p "Repo name [imsi-catcher]: " REPO_NAME
REPO_NAME="${REPO_NAME:-imsi-catcher}"

cd /home/engine/project/app

# Initialize git if not already
if [ ! -d .git ]; then
    git init
fi

# Create .gitignore
cat > .gitignore << 'GITIGNORE'
node_modules/
dist/
.output/
.env.local
.env.development.local
*.log
.DS_Store
convex/_generated/
GITIGNORE

# Update README with correct GitHub URL
sed -i "s/YOUR_USER/${GITHUB_USER}/g" README.md
sed -i "s/yourusername/${GITHUB_USER}/g" README.md

# Make scripts executable
chmod +x deploy/*.sh

# Add all files
git add -A

# Commit
git commit -m "Initial commit: IMSI Catcher anti-poaching surveillance system

- 3x Raspberry Pi 3B triangulation network with RTL-SDR
- Convex real-time backend with device management
- AI intelligence analyst powered by OpenRouter
- Dashboard with live feed, alerts, and triangulation map
- One-click deploy for Proxmox VM and Raspberry Pis"

# Create GitHub repo and push
echo ""
echo -e "${YELLOW}Creating GitHub repository...${NC}"
echo "Make sure you have the GitHub CLI installed (gh) or use the web UI."
echo ""

if command -v gh &>/dev/null; then
    gh repo create "${GITHUB_USER}/${REPO_NAME}" --public --push --source=. --remote=origin 2>/dev/null || {
        git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
        git push -u origin main 2>/dev/null || git push -u origin master
    }
else
    echo "GitHub CLI not found. Push manually:"
    echo ""
    echo "  1. Create repo at: https://github.com/new"
    echo "     Name: ${REPO_NAME}"
    echo "     Public"
    echo ""
    echo "  2. Push:"
    echo "     git remote add origin https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
    echo "     git push -u origin main"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "One-line install commands (after pushing):"
echo ""
echo "  Server:"
echo "    curl -sL https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/main/deploy/install.sh | bash -s server \\"
echo "      ${GITHUB_USER}/${REPO_NAME} your-domain.com YOUR_OPENROUTER_KEY"
echo ""
echo "  Pi:"
echo "    curl -sL https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/main/deploy/install.sh | bash -s pi \\"
echo "      Pi-Name -1.2921 36.8219 1800 http://YOUR_SERVER:3000"