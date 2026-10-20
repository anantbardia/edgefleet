# EdgeFleet Gateway Uninstallation Guide

To completely remove EdgeFleet from a Raspberry Pi 4:

### 1. Stop and Disable Services
```bash
sudo systemctl stop edgefleet-backend edgefleet-sync
sudo systemctl disable edgefleet-backend edgefleet-sync
sudo rm -f /etc/systemd/system/edgefleet-backend.service /etc/systemd/system/edgefleet-sync.service
sudo systemctl daemon-reload
```

### 2. Remove Nginx and Mosquitto Configurations
```bash
sudo rm -f /etc/nginx/sites-enabled/edgefleet.conf /etc/nginx/sites-available/edgefleet.conf
sudo rm -f /etc/mosquitto/conf.d/mosquitto-edgefleet.conf
sudo systemctl reload nginx
sudo systemctl restart mosquitto
```

### 3. Remove Application Directories & Data
```bash
sudo rm -rf /opt/edgefleet
sudo rm -rf /var/lib/edgefleet
sudo rm -rf /var/log/edgefleet
```

### 4. Remove System User
```bash
sudo userdel -r edgefleet 2>/dev/null || true
```
