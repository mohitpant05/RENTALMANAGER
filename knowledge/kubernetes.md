# Kubernetes (k3s) — Production Infrastructure

All resources in `k8s/` directory, namespace `rentmanager`.

## Manifests

| File | Resources |
|------|-----------|
| `namespace.yml` | Namespace `rentmanager` |
| `configmap.yml` | `rentmanager-config` — non-secret env vars (REDIS_URL, MEILI_URL, MINIO_ENDPOINT) |
| `secrets.yml` | `rentmanager-secrets` — template for DATABASE_URL, SECRET_KEY, etc. |
| `rbac.yml` | ServiceAccount `rentmanager-app` with minimal permissions |
| `backend.yml` | Backend Deployment (2 replicas) + Service :8000 |
| `frontend.yml` | Frontend Deployment (2 replicas) + Service :3000 |
| `celery.yml` | Celery worker + beat Deployments |
| `postgres.yml` | PostgreSQL StatefulSet + PVC + Service |
| `redis.yml` | Redis Deployment + PVC + Service |
| `meilisearch.yml` | Meilisearch Deployment + PVC + Service |
| `minio.yml` | MinIO Deployment + PVC + Service |
| `ingress.yml` | NGINX Ingress routing |
| `network-policies.yml` | Pod-to-pod traffic restrictions |
| `migration-job.yml` | One-shot Alembic migration Job |

## Network Architecture

```
Internet
  │
  ▼
NGINX Ingress Controller (ingress-nginx namespace)
  │
  ├─ /api/* ──→ backend Service:8000 (2 pods)
  └─ /*     ──→ frontend Service:3000 (2 pods)
                    │
                    │ SSR calls
                    ▼
              backend:8000 (via BACKEND_INTERNAL_URL)
```

### Network Policies (Zero-Trust)

Default: deny all ingress to all pods.

| Target Pod | Allowed From | Port |
|-----------|-------------|------|
| backend | ingress-nginx namespace, frontend pods | 8000 |
| frontend | ingress-nginx namespace | 3000 |
| postgres | backend, celery-worker, celery-beat | 5432 |
| redis | backend, celery-worker, celery-beat | 6379 |
| meilisearch | backend, celery-worker | 7700 |
| minio | backend | 9000 |

No pod can reach another pod unless explicitly allowed. Data stores only accessible from backend/celery.

## Ingress

NGINX Ingress Controller (not in namespace — runs cluster-wide in `ingress-nginx`).

```yaml
spec:
  ingressClassName: nginx
  rules:
    - http:
        paths:
          - path: /api      → backend:8000
          - path: /          → frontend:3000
```

No TLS configured in manifest (typically handled by cert-manager or cloud LB).
Proxy body size set to 50m for file uploads.

## Pod Security

All pods run with:
- `runAsNonRoot: true`, `runAsUser: 1000`
- `allowPrivilegeEscalation: false`
- `capabilities: drop: ["ALL"]`
- `automountServiceAccountToken: false`

## Resource Limits

Backend/Frontend pods:
- Requests: 256Mi memory, 250m CPU
- Limits: 512Mi memory, 500m CPU

## Health Checks

Backend:
- Readiness: `GET /api/health` (10s initial, 5s period)
- Liveness: `GET /api/health` (30s initial, 15s period)

Frontend:
- Readiness: `GET /` (10s initial, 5s period)
- Liveness: `GET /` (30s initial, 15s period)

## Deployment Strategy

Rolling update via `kubectl set image` (see `.github/workflows/deploy.yml`).
Backend init container runs `alembic upgrade head` before main container starts.

## Traffic Flow: Request → Tenant → Response

1. DNS → Load Balancer → NGINX Ingress
2. Ingress routes by path to backend/frontend Service
3. Service load-balances across pod replicas
4. Backend `TenantMiddleware` resolves tenant (see tenant-resolution.md)
5. DB session sets `search_path` to tenant schema
6. Response flows back through same chain
