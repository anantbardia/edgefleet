# Cloud Control Plane Deployment Guide

The EdgeFleet Cloud Control Plane aggregates telemetry, firmware releases, and rollout status across multiple distributed Raspberry Pi gateways into a centralized multi-tenant dashboard.

---

## 1. Cloud Architecture

```
                  ┌────────────────────────────────────────┐
                  │            Ubuntu 24.04 VPS            │
                  │                                        │
                  │   ┌────────┐   HTTPS   ┌───────────┐   │
Internet ────────►│   │ Nginx  │──────────►│  FastAPI  │   │
                  │   │ Proxy  │           │  Cloud    │   │
                  │   └────────┘           └─────┬─────┘   │
                  │                              │         │
                  │                        ┌─────▼─────┐   │
                  │                        │PostgreSQL │   │
                  │                        │    16     │   │
                  │                        └───────────┘   │
                  └────────────────────────────────────────┘
                                      ▲
                                      │ Outbound HTTPS (Batch Sync)
                    ┌─────────────────┴─────────────────┐
                    │                                   │
          ┌───────────────────┐               ┌───────────────────┐
          │ Gateway #1 (Site A│               │ Gateway #2 (Site B│
          │  Raspberry Pi 4)  │               │  Raspberry Pi 4)  │
          └───────────────────┘               └───────────────────┘
```

---

## 2. Prerequisites

- **Cloud VPS**: Ubuntu 22.04/24.04 LTS (e.g. Hetzner CX22, DigitalOcean Basic, AWS t3.small)
- **Domain Name**: Pointed via A record to the VPS IP (e.g. `fleet.yourcompany.com`)
- **Software**: Docker Engine and Docker Compose Plugin installed

---

## 3. Deployment Procedure

### 1. Clone Repository
```bash
git clone https://github.com/your-org/edgefleet.git /opt/edgefleet-cloud
cd /opt/edgefleet-cloud/deploy/cloud
```

### 2. Configure Environment Variables
```bash
cp .env.cloud.example .env.cloud
nano .env.cloud
```
Ensure you generate a strong secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Launch Docker Compose Stack
```bash
docker compose up -d --build
```

### 4. Verify Cloud Health
```bash
docker compose ps
curl -i http://localhost/api/health
```

---

## 4. Connecting Distributed Gateways

On each Raspberry Pi gateway, add the following configuration to `/opt/edgefleet/.env`:
```env
CLOUD_ENABLED=true
CLOUD_API_URL=https://fleet.yourcompany.com
CLOUD_API_KEY=your_generated_gateway_api_key
CLOUD_SYNC_INTERVAL_SECONDS=60
```
Then restart the gateway background service:
```bash
sudo systemctl restart edgefleet-backend
```
The gateway will now automatically batch-sync device status changes, rollout results, and alerts to the cloud control plane.
