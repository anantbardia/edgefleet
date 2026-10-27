#!/usr/bin/env bash
# ==============================================================================
# EdgeFleet — Instant Cloud Tunnel Launcher
# Usage: ./start-tunnel.sh
# ==============================================================================

set -e

# Terminal formatting colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "          EdgeFleet — Cloud Tunnel Launcher               "
echo "=========================================================="
echo -e "${NC}"

# Check and auto-fix DNS resolution if needed
if ! getent hosts api.trycloudflare.com >/dev/null 2>&1 && ! curl -s --connect-timeout 2 -I https://api.trycloudflare.com >/dev/null 2>&1; then
    echo -e "${YELLOW}[!] DNS lookup failed. Applying public DNS (1.1.1.1 / 8.8.8.8)...${NC}"
    echo -e "nameserver 1.1.1.1\nnameserver 8.8.8.8" | sudo tee /etc/resolv.conf >/dev/null 2>&1 || true
fi

# Detect active web port (default to port 80 for Nginx, fallback to 8000 for FastAPI)
PORT=80
if command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null http://127.0.0.1:80; then
        PORT=80
    elif curl -s -o /dev/null http://127.0.0.1:8000; then
        PORT=8000
    fi
fi

echo -e "${GREEN}[✓] Local EdgeFleet service active on port: ${BOLD}${PORT}${NC}"

# Check if cloudflared is installed
if ! command -v cloudflared >/dev/null 2>&1; then
    echo -e "${YELLOW}[!] cloudflared not found in PATH.${NC}"
    echo -e "${CYAN}[*] Auto-installing official cloudflared for Linux...${NC}"
    
    ARCH=$(uname -m)
    if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
        PKG_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
    elif [[ "$ARCH" == "armv7l" || "$ARCH" == "armhf" ]]; then
        PKG_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb"
    else
        PKG_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    fi

    if command -v dpkg >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
        echo -e "${CYAN}[*] Downloading from $PKG_URL...${NC}"
        curl -fsSL -o /tmp/cloudflared.deb "$PKG_URL"
        sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
        rm -f /tmp/cloudflared.deb
        echo -e "${GREEN}[✓] cloudflared successfully installed!${NC}"
    else
        echo -e "${YELLOW}[*] Falling back to zero-install SSH tunnel (Pinggy)...${NC}"
        exec ssh -p 443 -R0:localhost:${PORT} a.pinggy.io
    fi
fi

# Print clear instructions
echo -e "${GREEN}${BOLD}[✓] Starting Cloudflare Tunnel...${NC}"
echo -e "${CYAN}Your public cloud link will appear below (look for the https://*.trycloudflare.com link):${NC}"
echo "----------------------------------------------------------"

# Launch tunnel directly
exec cloudflared tunnel --url "http://localhost:${PORT}"
