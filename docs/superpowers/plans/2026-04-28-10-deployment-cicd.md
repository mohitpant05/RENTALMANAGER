# Deployment & CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Production-ready deployment configuration: multi-stage Dockerfiles, production docker-compose, Kubernetes manifests for k3s, GitHub Actions CI/CD pipeline (lint, test, build, push, deploy), and database migration automation.

**Architecture:** Multi-stage Docker builds for minimal production images. A `docker-compose.prod.yml` override removes dev volumes/reload. K8s manifests in `k8s/` cover all services as Deployments + Services, with ConfigMaps and Secrets for env config. GitHub Actions runs lint→test→build→push to ECR→deploy via kubectl. Alembic migrations run as an init container before backend starts.

**Tech Stack:** Docker, k3s (Kubernetes), GitHub Actions, AWS ECR, Alembic

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/Dockerfile` | Modified: multi-stage build (dev + prod targets) |
| `frontend/Dockerfile` | Modified: multi-stage build (dev + prod targets) |
| `docker-compose.prod.yml` | Production override (no volumes, no reload) |
| `.github/workflows/ci.yml` | CI: lint + test on PR |
| `.github/workflows/deploy.yml` | CD: build + push + deploy on main merge |
| `k8s/namespace.yml` | Kubernetes namespace |
| `k8s/configmap.yml` | Non-secret environment config |
| `k8s/secrets.yml` | Secret template (placeholder values) |
| `k8s/postgres.yml` | PostgreSQL StatefulSet |
| `k8s/redis.yml` | Redis Deployment |
| `k8s/meilisearch.yml` | Meilisearch Deployment |
| `k8s/minio.yml` | MinIO Deployment |
| `k8s/backend.yml` | Backend Deployment + Service |
| `k8s/celery.yml` | Celery worker + beat Deployments |
| `k8s/frontend.yml` | Frontend Deployment + Service |
| `k8s/ingress.yml` | Traefik IngressRoute |
| `k8s/migration-job.yml` | Alembic migration Job template |
| `backend/alembic/versions/0003_all_tables.py` | Migration for all current models |
| `scripts/deploy.sh` | Deployment helper script |

---

### Task 1: Multi-stage Dockerfiles

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Update backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Development target
FROM base AS dev
COPY pyproject.toml ./
RUN mkdir -p app && echo '__version__ = "0.1.0"' > app/__init__.py && \
    uv pip install --system ".[dev]" && \
    rm app/__init__.py
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production target
FROM base AS prod
COPY pyproject.toml ./
RUN mkdir -p app && echo '__version__ = "0.1.0"' > app/__init__.py && \
    uv pip install --system . && \
    rm app/__init__.py
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

- [ ] **Step 2: Update frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS base
WORKDIR /app

# Development target
FROM base AS dev
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production target
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci --only=production

FROM base AS builder
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM base AS prod
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./
EXPOSE 3000
CMD ["npm", "start"]
```

- [ ] **Step 3: Verify dev build still works**

Run: `docker compose build backend`

Expected: Builds successfully (uses dev target by default since docker-compose.yml doesn't specify target).

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile
git commit -m "build: add multi-stage Dockerfiles with dev and prod targets"
```

---

### Task 2: Production docker-compose override

**Files:**
- Create: `docker-compose.prod.yml`

- [ ] **Step 1: Create production override**

```yaml
# docker-compose.prod.yml
# Usage: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: prod
    volumes: []
    environment:
      DATABASE_URL: "postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"
      DATABASE_URL_SYNC: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"
      REDIS_URL: "redis://redis:6379/0"
      MEILI_URL: "http://meilisearch:7700"
      MEILI_MASTER_KEY: ${MEILI_MASTER_KEY}
      MINIO_ENDPOINT: "minio:9000"
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "false"
    restart: unless-stopped

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: prod
    volumes: []
    restart: unless-stopped

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: prod
    volumes: []
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: prod
    volumes: []
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
    restart: unless-stopped

  postgres:
    restart: unless-stopped

  redis:
    restart: unless-stopped

  meilisearch:
    environment:
      MEILI_ENV: production
    restart: unless-stopped

  minio:
    restart: unless-stopped

  traefik:
    restart: unless-stopped
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "build: add production docker-compose override"
```

---

### Task 3: Kubernetes manifests — infrastructure

**Files:**
- Create: `k8s/namespace.yml`
- Create: `k8s/configmap.yml`
- Create: `k8s/secrets.yml`
- Create: `k8s/postgres.yml`
- Create: `k8s/redis.yml`
- Create: `k8s/meilisearch.yml`
- Create: `k8s/minio.yml`

- [ ] **Step 1: Create namespace**

```yaml
# k8s/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: rentmanager
```

- [ ] **Step 2: Create configmap**

```yaml
# k8s/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rentmanager-config
  namespace: rentmanager
data:
  DATABASE_URL: "postgresql+asyncpg://rentmanager:$(POSTGRES_PASSWORD)@postgres:5432/rentmanager"
  DATABASE_URL_SYNC: "postgresql://rentmanager:$(POSTGRES_PASSWORD)@postgres:5432/rentmanager"
  REDIS_URL: "redis://redis:6379/0"
  MEILI_URL: "http://meilisearch:7700"
  MINIO_ENDPOINT: "minio:9000"
  DEBUG: "false"
  NEXT_PUBLIC_API_URL: "https://api.rentmanager.app"
```

- [ ] **Step 3: Create secrets template**

```yaml
# k8s/secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: rentmanager-secrets
  namespace: rentmanager
type: Opaque
stringData:
  POSTGRES_USER: rentmanager
  POSTGRES_PASSWORD: CHANGE_ME
  POSTGRES_DB: rentmanager
  SECRET_KEY: CHANGE_ME
  MEILI_MASTER_KEY: CHANGE_ME
  MINIO_ROOT_USER: CHANGE_ME
  MINIO_ROOT_PASSWORD: CHANGE_ME
```

- [ ] **Step 4: Create PostgreSQL StatefulSet**

```yaml
# k8s/postgres.yml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: rentmanager
spec:
  ports:
    - port: 5432
  selector:
    app: postgres
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: rentmanager
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:17-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: rentmanager-secrets
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: rentmanager-secrets
                  key: POSTGRES_PASSWORD
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: rentmanager-secrets
                  key: POSTGRES_DB
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "rentmanager"]
            initialDelaySeconds: 5
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

- [ ] **Step 5: Create Redis Deployment**

```yaml
# k8s/redis.yml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: rentmanager
spec:
  ports:
    - port: 6379
  selector:
    app: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: rentmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server", "--appendonly", "yes"]
          ports:
            - containerPort: 6379
          readinessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: redis-data
              mountPath: /data
      volumes:
        - name: redis-data
          emptyDir: {}
```

- [ ] **Step 6: Create Meilisearch Deployment**

```yaml
# k8s/meilisearch.yml
apiVersion: v1
kind: Service
metadata:
  name: meilisearch
  namespace: rentmanager
spec:
  ports:
    - port: 7700
  selector:
    app: meilisearch
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meilisearch
  namespace: rentmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: meilisearch
  template:
    metadata:
      labels:
        app: meilisearch
    spec:
      containers:
        - name: meilisearch
          image: getmeili/meilisearch:v1.12
          ports:
            - containerPort: 7700
          env:
            - name: MEILI_MASTER_KEY
              valueFrom:
                secretKeyRef:
                  name: rentmanager-secrets
                  key: MEILI_MASTER_KEY
            - name: MEILI_ENV
              value: production
          readinessProbe:
            httpGet:
              path: /health
              port: 7700
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: meili-data
              mountPath: /meili_data
      volumes:
        - name: meili-data
          emptyDir: {}
```

- [ ] **Step 7: Create MinIO Deployment**

```yaml
# k8s/minio.yml
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: rentmanager
spec:
  ports:
    - port: 9000
      name: api
    - port: 9001
      name: console
  selector:
    app: minio
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: rentmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: minio/minio:latest
          command: ["server", "/data", "--console-address", ":9001"]
          ports:
            - containerPort: 9000
            - containerPort: 9001
          env:
            - name: MINIO_ROOT_USER
              valueFrom:
                secretKeyRef:
                  name: rentmanager-secrets
                  key: MINIO_ROOT_USER
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: rentmanager-secrets
                  key: MINIO_ROOT_PASSWORD
          readinessProbe:
            httpGet:
              path: /minio/health/live
              port: 9000
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: minio-data
              mountPath: /data
      volumes:
        - name: minio-data
          emptyDir: {}
```

- [ ] **Step 8: Commit**

```bash
git add k8s/namespace.yml k8s/configmap.yml k8s/secrets.yml k8s/postgres.yml k8s/redis.yml k8s/meilisearch.yml k8s/minio.yml
git commit -m "infra(k8s): add infrastructure manifests (postgres, redis, meilisearch, minio)"
```

---

### Task 4: Kubernetes manifests — application

**Files:**
- Create: `k8s/backend.yml`
- Create: `k8s/celery.yml`
- Create: `k8s/frontend.yml`
- Create: `k8s/ingress.yml`
- Create: `k8s/migration-job.yml`

- [ ] **Step 1: Create backend Deployment**

```yaml
# k8s/backend.yml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: rentmanager
spec:
  ports:
    - port: 8000
  selector:
    app: backend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: rentmanager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      initContainers:
        - name: migrate
          image: ${ECR_REGISTRY}/rentmanager-backend:latest
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: rentmanager-config
            - secretRef:
                name: rentmanager-secrets
      containers:
        - name: backend
          image: ${ECR_REGISTRY}/rentmanager-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: rentmanager-config
            - secretRef:
                name: rentmanager-secrets
          readinessProbe:
            httpGet:
              path: /api/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

- [ ] **Step 2: Create Celery Deployments**

```yaml
# k8s/celery.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: rentmanager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
        - name: worker
          image: ${ECR_REGISTRY}/rentmanager-backend:latest
          command: ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
          envFrom:
            - configMapRef:
                name: rentmanager-config
            - secretRef:
                name: rentmanager-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
  namespace: rentmanager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-beat
  template:
    metadata:
      labels:
        app: celery-beat
    spec:
      containers:
        - name: beat
          image: ${ECR_REGISTRY}/rentmanager-backend:latest
          command: ["celery", "-A", "app.celery_app", "beat", "--loglevel=info"]
          envFrom:
            - configMapRef:
                name: rentmanager-config
            - secretRef:
                name: rentmanager-secrets
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
```

- [ ] **Step 3: Create frontend Deployment**

```yaml
# k8s/frontend.yml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: rentmanager
spec:
  ports:
    - port: 3000
  selector:
    app: frontend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: rentmanager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: ${ECR_REGISTRY}/rentmanager-frontend:latest
          ports:
            - containerPort: 3000
          env:
            - name: NEXT_PUBLIC_API_URL
              valueFrom:
                configMapKeyRef:
                  name: rentmanager-config
                  key: NEXT_PUBLIC_API_URL
          readinessProbe:
            httpGet:
              path: /
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

- [ ] **Step 4: Create Ingress**

```yaml
# k8s/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rentmanager-ingress
  namespace: rentmanager
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web,websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  rules:
    - host: "*.rentmanager.app"
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
```

- [ ] **Step 5: Create migration job template**

```yaml
# k8s/migration-job.yml
apiVersion: batch/v1
kind: Job
metadata:
  name: alembic-migrate
  namespace: rentmanager
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: ${ECR_REGISTRY}/rentmanager-backend:latest
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: rentmanager-config
            - secretRef:
                name: rentmanager-secrets
      restartPolicy: Never
  backoffLimit: 3
```

- [ ] **Step 6: Commit**

```bash
git add k8s/backend.yml k8s/celery.yml k8s/frontend.yml k8s/ingress.yml k8s/migration-job.yml
git commit -m "infra(k8s): add application manifests (backend, celery, frontend, ingress)"
```

---

### Task 5: GitHub Actions CI pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        working-directory: backend
        run: uv pip install --system ".[dev]"
      - name: Lint
        working-directory: backend
        run: ruff check .

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: rentmanager
          POSTGRES_PASSWORD: rentmanager_test
          POSTGRES_DB: rentmanager_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U rentmanager"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      meilisearch:
        image: getmeili/meilisearch:v1.12
        env:
          MEILI_MASTER_KEY: test_master_key
          MEILI_ENV: development
        ports:
          - 7700:7700
      minio:
        image: minio/minio:latest
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin_test
        ports:
          - 9000:9000
        options: >-
          --health-cmd "curl -f http://localhost:9000/minio/health/live"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        working-directory: backend
        run: uv pip install --system ".[dev]"
      - name: Run tests
        working-directory: backend
        env:
          DATABASE_URL: "postgresql+asyncpg://rentmanager:rentmanager_test@localhost:5432/rentmanager_test"
          DATABASE_URL_SYNC: "postgresql://rentmanager:rentmanager_test@localhost:5432/rentmanager_test"
          REDIS_URL: "redis://localhost:6379/0"
          MEILI_URL: "http://localhost:7700"
          MEILI_MASTER_KEY: test_master_key
          MINIO_ENDPOINT: "localhost:9000"
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin_test
          SECRET_KEY: test-secret-key
        run: pytest --tb=short -q
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI pipeline (lint + test)"
```

---

### Task 6: GitHub Actions CD pipeline

**Files:**
- Create: `.github/workflows/deploy.yml`
- Create: `scripts/deploy.sh`

- [ ] **Step 1: Create deploy workflow**

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Login to ECR
        id: ecr-login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push backend
        env:
          ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/rentmanager-backend:$IMAGE_TAG \
            -t $ECR_REGISTRY/rentmanager-backend:latest \
            --target prod backend/
          docker push $ECR_REGISTRY/rentmanager-backend:$IMAGE_TAG
          docker push $ECR_REGISTRY/rentmanager-backend:latest

      - name: Build and push frontend
        env:
          ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/rentmanager-frontend:$IMAGE_TAG \
            -t $ECR_REGISTRY/rentmanager-frontend:latest \
            --target prod frontend/
          docker push $ECR_REGISTRY/rentmanager-frontend:$IMAGE_TAG
          docker push $ECR_REGISTRY/rentmanager-frontend:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Deploy to k3s
        env:
          KUBECONFIG_DATA: ${{ secrets.KUBECONFIG }}
          ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          echo "$KUBECONFIG_DATA" | base64 -d > /tmp/kubeconfig
          export KUBECONFIG=/tmp/kubeconfig
          kubectl set image deployment/backend \
            backend=$ECR_REGISTRY/rentmanager-backend:$IMAGE_TAG \
            -n rentmanager
          kubectl set image deployment/celery-worker \
            worker=$ECR_REGISTRY/rentmanager-backend:$IMAGE_TAG \
            -n rentmanager
          kubectl set image deployment/celery-beat \
            beat=$ECR_REGISTRY/rentmanager-backend:$IMAGE_TAG \
            -n rentmanager
          kubectl set image deployment/frontend \
            frontend=$ECR_REGISTRY/rentmanager-frontend:$IMAGE_TAG \
            -n rentmanager
          kubectl rollout status deployment/backend -n rentmanager --timeout=120s
```

- [ ] **Step 2: Create deploy helper script**

```bash
#!/usr/bin/env bash
# scripts/deploy.sh — helper for manual k8s deployment
set -euo pipefail

NAMESPACE="rentmanager"

echo "Applying k8s manifests..."
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/secrets.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/postgres.yml
kubectl apply -f k8s/redis.yml
kubectl apply -f k8s/meilisearch.yml
kubectl apply -f k8s/minio.yml

echo "Waiting for infrastructure..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=60s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=60s

echo "Deploying application..."
kubectl apply -f k8s/backend.yml
kubectl apply -f k8s/celery.yml
kubectl apply -f k8s/frontend.yml
kubectl apply -f k8s/ingress.yml

echo "Waiting for rollout..."
kubectl rollout status deployment/backend -n $NAMESPACE --timeout=120s
kubectl rollout status deployment/frontend -n $NAMESPACE --timeout=120s

echo "Deploy complete!"
kubectl get pods -n $NAMESPACE
```

- [ ] **Step 3: Commit**

```bash
mkdir -p scripts
chmod +x scripts/deploy.sh
git add .github/workflows/deploy.yml scripts/deploy.sh
git commit -m "ci: add GitHub Actions deploy pipeline + k8s deploy script"
```

---

### Task 7: Alembic migration for current models

**Files:**
- Create: `backend/alembic/versions/0003_all_tables.py`

- [ ] **Step 1: Generate migration for all current models**

Run: `docker exec rm-backend alembic revision --autogenerate -m "add all phase1 tables" --rev-id 0003`

If autogenerate doesn't pick up changes (because we use `create_all` in tests), create manually:

```python
# backend/alembic/versions/0003_all_tables.py
"""add all phase1 tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenant_themes (public schema)
    op.create_table(
        "tenant_themes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("brand", postgresql.JSONB(), nullable=False),
        sa.Column("colors", postgresql.JSONB(), nullable=False),
        sa.Column("typography", postgresql.JSONB(), nullable=False),
        sa.Column("components", postgresql.JSONB(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_themes_tenant_id", "tenant_themes", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenant_themes_tenant_id")
    op.drop_table("tenant_themes")
```

Note: Tenant-scoped tables (resources, bookings, reviews, notifications, attachments) are created dynamically via `create_tenant_tables()` during tenant provisioning — they don't need Alembic migrations. Only public schema tables need them.

- [ ] **Step 2: Verify migration runs**

Run: `docker exec rm-backend alembic upgrade head`

Expected: Success (tables already exist via create_all, so this is a no-op or creates tenant_themes).

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0003_all_tables.py
git commit -m "migrate: add tenant_themes table migration"
```

---

### Task 8: Final verification

- [ ] **Step 1: Run full test suite**

Run: `docker exec rm-backend python -m pytest --tb=short -q`

Expected: 238 tests pass.

- [ ] **Step 2: Verify docker build (prod target)**

Run: `docker build --target prod -t rm-backend-test ./backend`

Expected: Builds successfully.

- [ ] **Step 3: Lint all new files**

Run: `docker exec rm-backend python -m ruff check .`

- [ ] **Step 4: Commit if needed**

```bash
git add -A && git commit -m "style: final cleanup" --allow-empty
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Docker containers | Task 1 (multi-stage Dockerfiles) |
| k3s Kubernetes | Tasks 3-4 (all k8s manifests) |
| Traefik as Ingress | Task 4 (ingress.yml) |
| CI/CD: GitHub Actions | Tasks 5-6 (ci.yml + deploy.yml) |
| Build → push to ECR → rolling deploy | Task 6 (deploy workflow) |
| Daily DB backups → S3 | Deferred (CronJob — add when AWS configured) |
| Alembic migrations | Task 7 (migration + init container in backend.yml) |
| Production config | Task 2 (prod compose) + Task 3 (configmap/secrets) |
