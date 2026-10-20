# EdgeFleet Cloud Control Plane

This directory provides the production container orchestration stack for deploying EdgeFleet on an Ubuntu Cloud VPS (DigitalOcean, AWS EC2, Hetzner, etc.).

## Quick Deployment

1. Copy `.env.cloud.example` to `.env.cloud` and set secure passwords and keys:
   ```bash
   cp .env.cloud.example .env.cloud
   nano .env.cloud
   ```

2. Start the stack:
   ```bash
   docker compose up -d --build
   ```

3. Check service health:
   ```bash
   docker compose ps
   curl -s http://localhost/api/health
   ```
