# Deployment

## Local Development

```bash
docker compose up          # starts all services
```

Services: postgres, redis, meilisearch, minio, traefik, backend, celery-worker, celery-beat, frontend

Traefik routes:
- Port 80: `/api/*` → backend:8000, `/*` → frontend:3000
- Port 8080: Traefik dashboard

Backend hot-reloads via volume mount (`./backend:/app`).
Frontend hot-reloads via volume mount with `.next` excluded.

## Docker Images

Both backend and frontend use multi-stage Dockerfiles with `dev` and `prod` targets.

**Dev**: volume mounts for hot reload, debug enabled
**Prod** (`docker-compose.prod.yml` overlay): no volumes, `restart: unless-stopped`, debug off

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## CI/CD Pipeline

### CI (`.github/workflows/ci.yml`)
Triggers: PR to main/prelive, push to main

Jobs:
1. **backend-lint** — `ruff check .`
2. **backend-test** — pytest against real Postgres/Redis/Meilisearch/MinIO services
3. **frontend-check** — TypeScript type check + Next.js lint

### Deploy (`.github/workflows/deploy.yml`)
Triggers: push to main, manual dispatch

Pipeline:
1. Run CI workflow (reusable)
2. **Build & push** — Docker build → AWS ECR (tagged `<sha>` + `latest`)
3. **Deploy** — `kubectl set image` rolling update on k3s cluster

Deploys: backend, celery-worker, celery-beat, frontend
Waits for rollout with 120s timeout.

## Environment Configuration

All config via env vars. See `backend/app/config.py` for full list.

Dev defaults hardcoded. Prod requires explicit env vars (no defaults for secrets).

Key secrets (GitHub Actions):
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — ECR push
- `KUBECONFIG` — base64-encoded kubeconfig for k3s cluster

## Image Registry

AWS ECR repositories:
- `rentmanager-backend`
- `rentmanager-frontend`
