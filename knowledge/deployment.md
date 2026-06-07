# Deployment

RentManager runs in a pair of Docker containers (backend + frontend) plus supporting services
(Postgres, Redis, Meilisearch, MinIO). Two local deployment approaches are supported:

| Approach | Runtime | Reverse Proxy | State |
|----------|---------|---------------|-------|
| **Docker Compose** | Docker Engine (Desktop, Colima) | Traefik | Legacy |
| **Kind K8s** | Docker Engine + Kind | nginx-ingress | Current |

---

## Prerequisites

### Docker Engine

Choose one:

| Engine | Install | Notes |
|--------|---------|-------|
| **Docker Desktop** | `brew install --cask docker` | GUI app, auto-updates, uses HyperKit/Virtualization.framework |
| **Colima** | `brew install colima && colima start` | Lightweight CLI-only, uses Lima+VZ, good for low-RAM machines |

Verify:
```bash
docker info
```

### Kind & Kubectl

Both install automatically via `scripts/preDeploy.sh`, or manually:

```bash
# macOS (Homebrew)
brew install kind kubectl

# Linux / no brew
curl -Lo /usr/local/bin/kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x /usr/local/bin/kind
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x /usr/local/bin/kubectl
```

---

## Option A: Docker Compose (Legacy)

### Start

```bash
# Dev (hot reload)
make up          # docker compose up -d
make logs        # tail all logs
make logs-backend

# Prod build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Architecture (old)

```
Host:80
  │
  ▼
Traefik (container, port 80)
  │
  ├── /api/* ──────► backend:8000
  │
  └── /* ──────────► frontend:3000
```

Traefik discovers services via Docker labels (`docker-compose.yml` lines 122-127, 183-188).

No labels needed on infra services (Postgres, Redis, etc.) — they're internal-only.

### Services & Ports

| Service | Internal Host | Container Port | Host Port |
|---------|--------------|---------------|-----------|
| Traefik | — | 80 | 80 |
| Traefik dashboard | — | 8080 | 8080 |
| Backend | backend:8000 | 8000 | 8000 |
| Frontend | frontend:3000 | 3000 | 3000 |
| Postgres | postgres:5432 | 5432 | 5432 |
| Redis | redis:6379 | 6379 | 6379 |
| Meilisearch | meilisearch:7700 | 7700 | 7700 |
| MinIO API | minio:9000 | 9000 | 9000 |
| MinIO Console | minio:9001 | 9001 | 9001 |

### Env File

Copy `.env.example` → `.env`. The dev defaults in `docker-compose.yml` work out of the box.

### Hot Reload

- **Backend**: `./backend:/app` volume mount, uvicorn `--reload`
- **Frontend**: `./frontend:/app` + `/app/node_modules` + `/app/.next` volume mounts, Turbopack

### Connections

Backend env vars (set in `docker-compose.yml`):

| Env | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `MEILI_URL` | `http://meilisearch:7700` |
| `MEILI_MASTER_KEY` | `masterkey_dev` |
| `MINIO_ENDPOINT` | `minio:9000` |
| `MINIO_PUBLIC_ENDPOINT` | `http://localhost:9000` |
| `NEXT_PUBLIC_API_URL` | `http://localhost/api` |

---

## Option B: Kind K8s (Current)

### One-command deploy

```bash
./scripts/preDeploy.sh
```

This does everything:
1. Checks / installs kind, kubectl, Docker
2. Creates Kind cluster `rentmanager` (port 80/443 mapped from host)
3. Builds Docker images (backend + frontend, prod target)
4. Loads images into Kind's containerd
5. Installs nginx-ingress controller
6. Applies K8s manifests for Postgres, Redis, Meilisearch, MinIO
7. Applies backend, celery, frontend, ingress manifests
8. Restarts all deployments to pick up fresh images
9. Seeds demo data + addons
10. Prints access URLs

### Architecture (current)

```
Host:80 ──► Kind node:80 ──► nginx-ingress pod:80
                                  │
                                  ▼
                          Ingress resource
                                  │
                          ├── /api ──────► backend Service ──► backend pod:8000
                          │
                          └── / ────────► frontend Service ──► frontend pod:3000
```

### K8s Manifests (`k8s/`)

| File | What it creates |
|------|----------------|
| `namespace.yml` | `rentmanager` namespace |
| `rbac.yml` | Service accounts (`rentmanager-app`, `rentmanager-data`) |
| `configmap.yml` | Non-sensitive env vars (REDIS_URL, MEILI_URL, etc.) |
| `secrets.yml` | Sensitive env vars (DB creds, SECRET_KEY, etc.) |
| `network-policies.yml` | Default-deny ingress + per-service allow rules |
| `postgres.yml` | StatefulSet + headless Service |
| `redis.yml` | StatefulSet + headless Service |
| `meilisearch.yml` | StatefulSet + headless Service |
| `minio.yml` | StatefulSet + headless Service (API :9000, Console :9001) |
| `backend.yml` | Deployment (2 replicas) + ClusterIP Service :8000 |
| `celery.yml` | Deployment for worker (2 replicas) + beat (1 replica) |
| `frontend.yml` | Deployment (2 replicas) + ClusterIP Service :3000 |
| `ingress.yml` | Ingress rule: `/api` → backend, `/` → frontend |

### Credentials (seeded)

| Role | Email | Password |
|------|-------|----------|
| Superadmin | `platform@rentmanager.dev` | `platform123` |
| Tenant Admin | `admin@rentmanager.dev` | `admin123` |
| Lister | `lister@rentmanager.dev` | `lister123` |
| Customer | `alice@rentmanager.dev` | `alice123` |
| Customer | `bob@rentmanager.dev` | `bob123` |

### Re-deploy

```bash
./scripts/preDeploy.sh
```

Safe to re-run. Existing cluster is reused, images are rebuilt and reloaded, pods are
restarted via `kubectl rollout restart`.

### Tear down

```bash
kind delete cluster --name rentmanager
```

---

## Option C: Colima (Docker Engine Alternative)

Colima is a lightweight Docker runtime for macOS that uses Lima + VZ instead of
Docker Desktop's HyperKit. It consumes less RAM and has no GUI.

### Setup

```bash
# Install
brew install colima

# Start (recommended: 4GB RAM, 2 CPUs)
colima start --memory 4 --cpu 2

# Verify
docker info
```

### Usage with RentManager

Both deployment approaches work identically with Colima:

```bash
# Docker Compose
COLIMA_PROFILE=default docker compose up -d

# Kind (preDeploy.sh detects Docker automatically)
./scripts/preDeploy.sh
```

The only difference: `colima stop`/`colima start` replaces Docker Desktop's menu bar
controls.

### Colima vs Docker Desktop

| Aspect | Docker Desktop | Colima |
|--------|---------------|--------|
| RAM usage | ~2-3GB idle | ~500MB idle |
| GUI | Yes | No |
| Start/stop | Menu bar | CLI (`colima start/stop`) |
| VM backend | HyperKit / Virtualization.framework | Lima + VZ |
| Kubernetes | Bundled (can be enabled) | Via Kind |
| Docker socket | `~/.docker/run/docker.sock` | `~/.colima/default/docker.sock` |

### Stop / Restart

```bash
colima stop          # frees RAM
colima start         # resumes from existing VM
colima delete        # destroys VM entirely
```

---

## Migration: Docker Compose → Kind K8s

| Concern | Docker Compose | Kind K8s |
|---------|---------------|----------|
| Reverse proxy | Traefik (Docker labels) | nginx-ingress (Ingress resource) |
| Routing config | `docker-compose.yml` labels | `k8s/ingress.yml` |
| Service discovery | Docker DNS (service names) | K8s DNS (Service names) |
| Secrets | `.env` file | `k8s/secrets.yml` + `k8s/configmap.yml` |
| Port 80 | Traefik container | nginx-ingress pod (hostPort) |
| Build | `docker compose build` | `docker build` + `kind load docker-image` |
| Data persistence | Named volumes | PVC on Kind's `local-path` StorageClass |
| Teardown | `make down` + `docker volume rm` | `kind delete cluster` |

### Key differences in env vars

The `NEXT_PUBLIC_API_URL` in Docker Compose is `http://localhost/api`. In K8s
(`frontend.yml` line 42) it's set to `/api` — the ingress handles the full URL,
so a relative path works.

---

## Command Reference

### Docker Compose

```bash
make up              # start all services (detached)
make down            # stop all services
make down-clean      # stop + delete volumes (wipes DB!)
make logs            # tail all logs
make build           # rebuild images
make test            # pytest inside backend container
make migrate         # alembic upgrade head
make psql            # psql to postgres
make redis-cli       # redis-cli to redis
```

### Kind K8s

```bash
./scripts/preDeploy.sh                    # full deploy

kubectl get pods -n rentmanager           # list pods
kubectl get svc -n rentmanager            # list services
kubectl logs -n rentmanager deploy/backend  # backend logs
kubectl exec -n rentmanager deploy/backend -- python -m scripts.seed_demo

kind delete cluster --name rentmanager    # full teardown
kind get clusters                         # list kind clusters
```

### Seed (Both)

```bash
# Run all seeds
kubectl exec -n rentmanager deploy/backend -- python -m scripts.seed_demo
kubectl exec -n rentmanager deploy/backend -- python -m scripts.seed_addons

# For Docker Compose, replace kubectl exec with:
docker compose exec backend python -m scripts.seed_dev
```

---

## Troubleshooting

### Port 80 in use

```bash
sudo lsof -i :80 -P -n | grep LISTEN
```

If it's a previous Kind cluster: `kind delete cluster --name rentmanager`
If it's something else: stop that process first.

### Pod stuck in CrashLoopBackOff

```bash
kubectl describe pod -n rentmanager <pod-name>
kubectl logs -n rentmanager <pod-name> --tail=50
```

Common causes: migration failure, OOMKilled (increase memory in `k8s/backend.yml`),
Redis connection refused (check `--protected-mode` in `k8s/redis.yml`).

### OOMKilled

The backend with 4 workers + 2 replicas can exceed 512Mi. Fix in `k8s/backend.yml`:
reduce workers or increase `limits.memory`.

### Colima: Docker not found

```bash
# Ensure colima is running
colima status
colima start

# Docker context should point to colima
docker context ls
docker context use default
```

### Docker Desktop vs Colima context

```bash
# Docker Desktop
docker context use desktop-linux

# Colima
docker context use default
```

Both work with `preDeploy.sh` — it uses whatever `docker info` responds to.
