#!/usr/bin/env bash
# ==============================================================================
# EdgeFleet — Instant Cloud & Local Tunnel Launcher
# Usage: ./start-tunnel.sh
# ==============================================================================

set -e

echo "=========================================================="
echo "          EdgeFleet — Gateway & Cloud Launcher            "
echo "=========================================================="

# 1. Display Current Network & Local Access Info
CURRENT_IPS=$(hostname -I 2>/dev/null || echo "127.0.0.1")
PRIMARY_IP=$(echo "$CURRENT_IPS" | awk '{print $1}')
HOST_NAME=$(hostname 2>/dev/null || echo "raspberrypi")

echo "[*] Local Gateway IP Address : http://${PRIMARY_IP}"
echo "[*] Zero-Config Local URL    : http://${HOST_NAME}.local"
echo "----------------------------------------------------------"

# 2. Check and auto-fix DNS resolution if needed
if ! getent hosts api.trycloudflare.com >/dev/null 2>&1 && ! curl -s --connect-timeout 2 -I https://api.trycloudflare.com >/dev/null 2>&1; then
    echo "[!] DNS lookup failed. Applying public DNS (1.1.1.1 / 8.8.8.8)..."
    echo -e "nameserver 1.1.1.1\nnameserver 8.8.8.8" | sudo tee /etc/resolv.conf >/dev/null 2>&1 || true
fi

# 3. Detect active web port (default to port 80 for Nginx, fallback to 8000 for FastAPI)
PORT=80
if command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null http://127.0.0.1:80; then
        PORT=80
    elif curl -s -o /dev/null http://127.0.0.1:8000; then
        PORT=8000
    fi
fi

echo "[✓] Local EdgeFleet service active on port: ${PORT}"

# 4. Check if cloudflared is installed; install if missing
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "[!] cloudflared not found in PATH."
    echo "[*] Auto-installing official cloudflared for Linux..."
    
    ARCH=$(uname -m)
    if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
        PKG_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
    elif [[ "$ARCH" == "armv7l" || "$ARCH" == "armhf" ]]; then
        PKG_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb"
    else
        PKG_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    fi

    if command -v dpkg >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
        curl -fsSL -o /tmp/cloudflared.deb "$PKG_URL"
        sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
        rm -f /tmp/cloudflared.deb
    fi
fi

# 5. Launch Cloud Tunnel (Cloudflare with automatic SSH Pinggy fallback)
echo "[✓] Starting Cloud Tunnel..."
echo "Your public cloud link will appear below:"
echo "----------------------------------------------------------"

if command -v cloudflared >/dev/null 2>&1; then
    set +e
    cloudflared tunnel --url "http://localhost:${PORT}"
    CF_EXIT=$?
    set -e

    if [ $CF_EXIT -ne 0 ]; then
        echo ""
        echo "[!] Cloudflare Tunnel hit a TLS/network error (exit code: $CF_EXIT)."
        echo "[*] Switching automatically to zero-cert SSH Tunnel (Pinggy)..."
        echo "----------------------------------------------------------"
        exec ssh -p 443 -o StrictHostKeyChecking=no -R0:localhost:${PORT} a.pinggy.io
    fi
else
    echo "[*] Launching zero-install SSH Cloud Tunnel (Pinggy)..."
    exec ssh -p 443 -o StrictHostKeyChecking=no -R0:localhost:${PORT} a.pinggy.io
fi
