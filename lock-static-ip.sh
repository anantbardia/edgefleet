#!/usr/bin/env bash
# ==============================================================================
# EdgeFleet — Static IP & Network Management Script
# Usage:
#   sudo ./lock-static-ip.sh              # Locks CURRENT IP permanently
#   sudo ./lock-static-ip.sh 192.168.1.50 # Sets and locks a CUSTOM IP
#   sudo ./lock-static-ip.sh auto         # Reverts back to dynamic DHCP
# ==============================================================================

set -e

# Require root
if [ "$EUID" -ne 0 ]; then
  echo ""
  echo "[-] ERROR: This script must be run with sudo privileges."
  echo "    Please run: sudo ./lock-static-ip.sh [IP | auto]"
  echo ""
  exit 1
fi

MODE="${1:-lock_current}"

echo "=========================================================="
echo "          EdgeFleet — Network & IP Configuration          "
echo "=========================================================="

# 1. Identify active interface
ACTIVE_IFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
if [ -z "$ACTIVE_IFACE" ]; then
  ACTIVE_IFACE=$(ip -br link | grep -E 'wlan0|eth0' | grep 'UP' | awk '{print $1}' | head -n1)
fi

if [ -z "$ACTIVE_IFACE" ]; then
  echo "[-] ERROR: No active Wi-Fi (wlan0) or Ethernet (eth0) interface found."
  echo "    Please verify network connection and try again."
  exit 1
fi

# Detect NetworkManager connection name
CON_NAME=""
if command -v nmcli >/dev/null 2>&1; then
  CON_NAME=$(nmcli -t -f NAME,DEVICE connection show --active | grep ":$ACTIVE_IFACE" | cut -d: -f1 | head -n1)
  if [ -z "$CON_NAME" ]; then
    CON_NAME=$(nmcli -t -f NAME,DEVICE connection show | grep ":$ACTIVE_IFACE" | cut -d: -f1 | head -n1)
  fi
fi

# ------------------------------------------------------------------------------
# CASE A: Revert back to Dynamic DHCP
# ------------------------------------------------------------------------------
if [ "$MODE" = "auto" ] || [ "$MODE" = "dhcp" ]; then
  echo "[*] Switching interface $ACTIVE_IFACE back to automatic DHCP..."

  if [ -n "$CON_NAME" ]; then
    nmcli connection modify "$CON_NAME" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns ""
    nmcli connection up "$CON_NAME" >/dev/null 2>&1 || true
    echo "[✓] NetworkManager connection '$CON_NAME' restored to DHCP!"
  elif [ -f /etc/dhcpcd.conf ]; then
    sed -i "/^interface $ACTIVE_IFACE/,+4d" /etc/dhcpcd.conf
    systemctl restart dhcpcd >/dev/null 2>&1 || true
    echo "[✓] Removed static block from /etc/dhcpcd.conf!"
  fi

  NEW_IP=$(hostname -I | awk '{print $1}')
  echo "[✓] Dynamic DHCP active. Current assigned IP is: http://$NEW_IP"
  exit 0
fi

# ------------------------------------------------------------------------------
# CASE B: Lock Current or Custom Static IP
# ------------------------------------------------------------------------------
CURRENT_IP=$(ip -4 addr show dev "$ACTIVE_IFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1)
SUBNET_CIDR=$(ip -4 addr show dev "$ACTIVE_IFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}/\d+' | head -n1 | cut -d/ -f2)
GATEWAY_IP=$(ip route | grep '^default' | awk '{print $3}' | head -n1)
MAC_ADDR=$(cat "/sys/class/net/$ACTIVE_IFACE/address" 2>/dev/null || echo "Unknown")

[ -z "$SUBNET_CIDR" ] && SUBNET_CIDR="24"

TARGET_IP="$CURRENT_IP"
if [ "$MODE" != "lock_current" ]; then
  # User specified a custom IP
  TARGET_IP="$MODE"
fi

if [ -z "$TARGET_IP" ] || [ -z "$GATEWAY_IP" ]; then
  echo "[-] ERROR: Unable to determine valid IP address or Gateway."
  exit 1
fi

echo "[*] Active Network Interface : $ACTIVE_IFACE"
echo "[*] Target Static IP         : $TARGET_IP"
echo "[*] Gateway / Router IP      : $GATEWAY_IP"
echo "[*] Subnet Mask Prefix       : /$SUBNET_CIDR"
echo "[*] MAC Address              : $MAC_ADDR"
echo ""

# Apply via NetworkManager or dhcpcd
if [ -n "$CON_NAME" ]; then
  echo "[*] Applying static IP via NetworkManager on '$CON_NAME'..."
  nmcli connection modify "$CON_NAME" \
    ipv4.method manual \
    ipv4.addresses "$TARGET_IP/$SUBNET_CIDR" \
    ipv4.gateway "$GATEWAY_IP" \
    ipv4.dns "1.1.1.1 8.8.8.8"
  
  nmcli connection up "$CON_NAME" >/dev/null 2>&1 || true
  echo "[✓] Network profile '$CON_NAME' successfully locked!"
elif [ -f /etc/dhcpcd.conf ]; then
  echo "[*] Applying static IP in /etc/dhcpcd.conf..."
  sed -i "/^interface $ACTIVE_IFACE/,+4d" /etc/dhcpcd.conf
  cat <<EOF >> /etc/dhcpcd.conf

interface $ACTIVE_IFACE
static ip_address=$TARGET_IP/$SUBNET_CIDR
static routers=$GATEWAY_IP
static domain_name_servers=1.1.1.1 8.8.8.8
EOF
  systemctl restart dhcpcd >/dev/null 2>&1 || true
  echo "[✓] Static configuration written to /etc/dhcpcd.conf!"
fi

# Enable Avahi mDNS daemon for domain resolution (http://raspberrypi.local)
if command -v systemctl >/dev/null 2>&1; then
  systemctl enable --now avahi-daemon >/dev/null 2>&1 || true
fi

echo ""
echo "=========================================================="
echo "             STATIC IP CONFIGURATION APPLIED              "
echo "=========================================================="
echo "[✓] Static IP locked to: http://$TARGET_IP"
echo "[✓] Local hostname:      http://$(hostname).local (or http://raspberrypi.local)"
echo ""
echo "[*] Options:"
echo "    - To change to another IP:  sudo ./lock-static-ip.sh <NEW_IP>"
echo "    - To revert back to DHCP:   sudo ./lock-static-ip.sh auto"
echo "=========================================================="
