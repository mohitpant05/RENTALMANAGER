# Infrastructure & Backend Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the complete development infrastructure — Docker Compose with all services, backend/frontend scaffolds, database layer with multi-tenant schema routing, and health checks — so subsequent plans can build features on a running stack.

**Architecture:** Modular monolith. FastAPI backend + Next.js 15 frontend behind Traefik reverse proxy. PostgreSQL schema-per-tenant isolation. All services containerized with named volumes for data persistence.

**Tech Stack:** FastAPI, SQLModel, Alembic, Next.js 15, Tailwind CSS v4, PostgreSQL 17, Redis 7, Meilisearch, MinIO, Traefik v3, Celery, Docker Compose, uv

**Note:** This is **Plan 1 of 9** for Phase 1 MVP. Subsequent plans:
2. Auth & RBAC
3. Tenancy Engine & White-Label Theming
4. Generic Resource Engine
5. Booking Engine
6. Search & Discovery
7. Reviews & Notifications
8. Admin Panel + Public Frontend
9. CI/CD & Deployment

---

## File Map

```
RM/
├── docker-compose.yml           — all services orchestration
├── .env.example                 — environment template
├── .env                         — local environment (gitignored)
├── .gitignore                   — updated with new ignores
├── Makefile                     — common dev commands
├── traefik/
│   └── traefik.yml              — static Traefik config
├── backend/
│   ├── Dockerfile               — Python 3.12 + uv
│   ├── .dockerignore            — build context excludes
│   ├── pyproject.toml           — dependencies + project config
│   ├── alembic.ini              — Alembic config
│   ├── alembic/
│   │   ├── env.py               — async migration runner
│   │   ├── script.py.mako       — migration template
│   │   └── versions/
│   │       └── 0001_public_schema.py — tenants + config tables
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              — FastAPI app + lifespan
│   │   ├── config.py            — pydantic-settings
│   │   ├── database.py          — async engine + session factory
│   │   ├── celery_app.py        — Celery instance
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── tenancy/
│   │       │   ├── __init__.py
│   │       │   ├── models.py    — Tenant, TenantDomain, PlatformConfig
│   │       │   ├── middleware.py — tenant resolution middleware
│   │       │   └── context.py   — request-scoped tenant context
│   │       └── common/
│   │           ├── __init__.py
│   │           └── models.py    — TimestampMixin, UUIDMixin
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py          — fixtures: async client, test DB
│       ├── test_health.py       — health endpoint tests
│       └── test_tenancy.py      — tenant resolution tests
├── frontend/
│   ├── Dockerfile               — Node 22 dev server
│   ├── .dockerignore
│   ├── package.json             — Next.js 15 + Tailwind v4
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   └── src/
│       ├── app/
│       │   ├── layout.tsx       — root layout
│       │   └── page.tsx         — landing page
│       └── styles/
│           └── globals.css      — Tailwind v4 import
└── docs/                        — (already exists)
```

---

### Task 1: Project Root — Docker Compose + Environment

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.env`
- Create: `Makefile`
- Modify: `.gitignore`

- [ ] **Step 1: Write `.env.example`**

```env
# PostgreSQL
POSTGRES_USER=rentmanager
POSTGRES_PASSWORD=rentmanager_dev
POSTGRES_DB=rentmanager
POSTGRES_PORT=5432

# Redis
REDIS_PORT=6379

# Meilisearch
MEILI_MASTER_KEY=masterkey_dev
MEILI_PORT=7700

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin_dev
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001

# Backend
BACKEND_PORT=8000
SECRET_KEY=dev-secret-key-change-in-production

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost/api
```

- [ ] **Step 2: Copy to `.env`**

```bash
cp .env.example .env
```

- [ ] **Step 3: Update `.gitignore`**

```gitignore
# Environment
.env
!.env.example

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.ruff_cache/
*.egg-info/
.venv/

# Node
node_modules/
.next/

# Docker
.docker/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Superpowers
.superpowers/

# MinIO data (if running locally outside Docker)
data/
```

- [ ] **Step 4: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:17-alpine
    container_name: rm-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-rentmanager}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-rentmanager_dev}
      POSTGRES_DB: ${POSTGRES_DB:-rentmanager}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-rentmanager}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - rentmanager

  redis:
    image: redis:7-alpine
    container_name: rm-redis
    command: redis-server --appendonly yes
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - rentmanager

  meilisearch:
    image: getmeili/meilisearch:v1.12
    container_name: rm-meilisearch
    environment:
      MEILI_MASTER_KEY: ${MEILI_MASTER_KEY:-masterkey_dev}
      MEILI_ENV: development
    ports:
      - "${MEILI_PORT:-7700}:7700"
    volumes:
      - meilisearch_data:/meili_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7700/health"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - rentmanager

  minio:
    image: minio/minio:latest
    container_name: rm-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin_dev}
    command: server /data --console-address ":9001"
    ports:
      - "${MINIO_API_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - rentmanager

  traefik:
    image: traefik:v3.2
    container_name: rm-traefik
    ports:
      - "80:80"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik:/etc/traefik:ro
    depends_on:
      backend:
        condition: service_started
      frontend:
        condition: service_started
    networks:
      - rentmanager

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: rm-backend
    environment:
      DATABASE_URL: "postgresql+asyncpg://${POSTGRES_USER:-rentmanager}:${POSTGRES_PASSWORD:-rentmanager_dev}@postgres:5432/${POSTGRES_DB:-rentmanager}"
      DATABASE_URL_SYNC: "postgresql://${POSTGRES_USER:-rentmanager}:${POSTGRES_PASSWORD:-rentmanager_dev}@postgres:5432/${POSTGRES_DB:-rentmanager}"
      REDIS_URL: "redis://redis:6379/0"
      MEILI_URL: "http://meilisearch:7700"
      MEILI_MASTER_KEY: ${MEILI_MASTER_KEY:-masterkey_dev}
      MINIO_ENDPOINT: "minio:9000"
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin_dev}
      SECRET_KEY: ${SECRET_KEY:-dev-secret-key-change-in-production}
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      meilisearch:
        condition: service_healthy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=PathPrefix(`/api`)"
      - "traefik.http.routers.backend.entrypoints=web"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
    networks:
      - rentmanager

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: rm-celery-worker
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: "postgresql+asyncpg://${POSTGRES_USER:-rentmanager}:${POSTGRES_PASSWORD:-rentmanager_dev}@postgres:5432/${POSTGRES_DB:-rentmanager}"
      DATABASE_URL_SYNC: "postgresql://${POSTGRES_USER:-rentmanager}:${POSTGRES_PASSWORD:-rentmanager_dev}@postgres:5432/${POSTGRES_DB:-rentmanager}"
      REDIS_URL: "redis://redis:6379/0"
      MEILI_URL: "http://meilisearch:7700"
      MEILI_MASTER_KEY: ${MEILI_MASTER_KEY:-masterkey_dev}
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - rentmanager

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: rm-celery-beat
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      REDIS_URL: "redis://redis:6379/0"
    volumes:
      - ./backend:/app
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - rentmanager

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: rm-frontend
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost/api}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=PathPrefix(`/`)"
      - "traefik.http.routers.frontend.entrypoints=web"
      - "traefik.http.routers.frontend.priority=1"
      - "traefik.http.services.frontend.loadbalancer.server.port=3000"
    networks:
      - rentmanager

volumes:
  postgres_data:
    name: rm_postgres_data
  redis_data:
    name: rm_redis_data
  meilisearch_data:
    name: rm_meilisearch_data
  minio_data:
    name: rm_minio_data

networks:
  rentmanager:
    name: rm_network
    driver: bridge
```

- [ ] **Step 5: Write `Makefile`**

```makefile
.PHONY: up down build logs test migrate shell psql redis-cli

up:
	docker compose up -d

up-build:
	docker compose up -d --build

down:
	docker compose down

down-clean:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

test:
	docker compose exec backend pytest -v

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

shell:
	docker compose exec backend bash

psql:
	docker compose exec postgres psql -U $${POSTGRES_USER:-rentmanager} -d $${POSTGRES_DB:-rentmanager}

redis-cli:
	docker compose exec redis redis-cli

status:
	docker compose ps
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example .gitignore Makefile
git commit -m "infra: add Docker Compose with PostgreSQL, Redis, Meilisearch, MinIO, Traefik"
```

---

### Task 2: Traefik Configuration

**Files:**
- Create: `traefik/traefik.yml`

- [ ] **Step 1: Create directory and write Traefik static config**

```bash
mkdir -p traefik
```

Write `traefik/traefik.yml`:

```yaml
api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":80"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: rm_network

log:
  level: INFO

accessLog: {}
```

- [ ] **Step 2: Commit**

```bash
git add traefik/
git commit -m "infra: add Traefik reverse proxy configuration"
```

---

### Task 3: Backend Project Scaffold

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "rentmanager-backend"
version = "0.1.0"
description = "RentManager - Multi-tenant rental management platform"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115",
    "sqlmodel>=0.0.22",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic-settings>=2.7",
    "redis>=5.2",
    "celery[redis]>=5.4",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "httpx>=0.28",
    "meilisearch-python>=0.33",
    "minio>=7.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

- [ ] **Step 2: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies (cached layer)
COPY pyproject.toml ./
RUN mkdir -p app && echo '__version__ = "0.1.0"' > app/__init__.py && \
    uv pip install --system ".[dev]" && \
    rm app/__init__.py

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 3: Write `backend/.dockerignore`**

```
__pycache__
*.pyc
*.pyo
.pytest_cache
.ruff_cache
.venv
.env
*.egg-info
.git
```

- [ ] **Step 4: Write `backend/app/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Write `backend/app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rentmanager:rentmanager_dev@localhost:5432/rentmanager"
    database_url_sync: str = "postgresql://rentmanager:rentmanager_dev@localhost:5432/rentmanager"
    redis_url: str = "redis://localhost:6379/0"
    meili_url: str = "http://localhost:7700"
    meili_master_key: str = "masterkey_dev"
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin_dev"
    secret_key: str = "dev-secret-key-change-in-production"

    debug: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Write `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Startup: verify connections
    print(f"Starting RentManager backend (debug={settings.debug})")
    yield
    # Shutdown
    print("Shutting down RentManager backend")


app = FastAPI(
    title="RentManager API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI project with config and health endpoint"
```

---

### Task 4: Frontend Project Scaffold

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/styles/globals.css`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "rentmanager-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.1",
    "react": "^19",
    "react-dom": "^19"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4",
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: Write `frontend/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 3: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Write `frontend/postcss.config.mjs`**

```javascript
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

- [ ] **Step 5: Create directories and write layout + page**

```bash
mkdir -p frontend/src/app frontend/src/styles frontend/public
```

Write `frontend/src/styles/globals.css`:

```css
@import "tailwindcss";
```

Write `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "RentManager",
  description: "Multi-tenant rental management platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
```

Write `frontend/src/app/page.tsx`:

```tsx
export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">RentManager</h1>
        <p className="mt-4 text-lg text-gray-600">
          Multi-tenant rental management platform
        </p>
      </div>
    </main>
  );
}
```

- [ ] **Step 6: Write `frontend/Dockerfile`**

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

- [ ] **Step 7: Write `frontend/.dockerignore`**

```
node_modules
.next
.env
.git
```

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js 15 with Tailwind CSS v4"
```

---

### Task 5: Database Layer + Alembic Setup

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/common/__init__.py`
- Create: `backend/app/core/common/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Write `backend/app/core/__init__.py` and `backend/app/core/common/__init__.py`**

```bash
mkdir -p backend/app/core/common
```

Both files are empty `__init__.py`:

```python
```

- [ ] **Step 2: Write `backend/app/core/common/models.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class UUIDMixin(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 3: Write `backend/app/database.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from sqlmodel import SQLModel

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_tenant_session(tenant_schema: str) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        await session.execute(text(f"SET search_path TO {tenant_schema}, public"))
        yield session
        await session.execute(text("SET search_path TO public"))


async def create_tenant_schema(session: AsyncSession, tenant_id: str) -> None:
    schema_name = f"tenant_{tenant_id.replace('-', '_')}"
    await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await session.commit()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

- [ ] **Step 4: Write `backend/alembic.ini`**

```ini
[alembic]
script_location = alembic

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 5: Create alembic directory and write `backend/alembic/script.py.mako`**

```bash
mkdir -p backend/alembic/versions
```

Write `backend/alembic/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 6: Write `backend/alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from app.config import get_settings

# Import all models so they register with SQLModel.metadata
from app.core.tenancy.models import Tenant, TenantDomain  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/database.py backend/app/core/ backend/alembic.ini backend/alembic/
git commit -m "feat(backend): add async database layer and Alembic migration setup"
```

---

### Task 6: Public Schema Models — Tenant + Platform Config

**Files:**
- Create: `backend/app/core/tenancy/__init__.py`
- Create: `backend/app/core/tenancy/models.py`
- Create: `backend/alembic/versions/0001_public_schema.py`

- [ ] **Step 1: Create tenancy module**

```bash
mkdir -p backend/app/core/tenancy
touch backend/app/core/tenancy/__init__.py
```

- [ ] **Step 2: Write `backend/app/core/tenancy/models.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, unique=True, index=True)
    schema_name: str = Field(max_length=100, unique=True)
    is_active: bool = Field(default=True)
    config: dict | None = Field(default=None, sa_column=Column(JSONB))
    base_currency: str = Field(default="USD", max_length=3)
    timezone: str = Field(default="UTC", max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenantDomain(SQLModel, table=True):
    __tablename__ = "tenant_domains"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    domain: str = Field(max_length=255, unique=True, index=True)
    is_primary: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlatformConfig(SQLModel, table=True):
    __tablename__ = "platform_config"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(max_length=100, unique=True, index=True)
    value: str = Field(sa_column=Column(Text))
    description: str | None = Field(default=None, max_length=500)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 3: Write initial migration `backend/alembic/versions/0001_public_schema.py`**

```python
"""create public schema tables

Revision ID: 0001
Revises:
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("schema_name", sa.String(100), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "tenant_domains",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tenant_domains_domain", "tenant_domains", ["domain"])
    op.create_index("ix_tenant_domains_tenant_id", "tenant_domains", ["tenant_id"])

    op.create_table(
        "platform_config",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_platform_config_key", "platform_config", ["key"])


def downgrade() -> None:
    op.drop_table("platform_config")
    op.drop_table("tenant_domains")
    op.drop_table("tenants")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/tenancy/ backend/alembic/versions/0001_public_schema.py
git commit -m "feat(backend): add tenant models and initial migration"
```

---

### Task 7: Multi-Tenant Middleware + Tenant Context

**Files:**
- Create: `backend/app/core/tenancy/context.py`
- Create: `backend/app/core/tenancy/middleware.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write `backend/app/core/tenancy/context.py`**

```python
from contextvars import ContextVar
from dataclasses import dataclass

from app.core.tenancy.models import Tenant


@dataclass
class TenantContext:
    tenant: Tenant
    schema_name: str


_tenant_ctx: ContextVar[TenantContext | None] = ContextVar("tenant_ctx", default=None)


def get_current_tenant() -> TenantContext | None:
    return _tenant_ctx.get()


def set_current_tenant(ctx: TenantContext | None) -> None:
    _tenant_ctx.set(ctx)
```

- [ ] **Step 2: Write `backend/app/core/tenancy/middleware.py`**

```python
import re

from fastapi import Request
from sqlmodel import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.database import async_session_factory
from app.core.tenancy.context import TenantContext, set_current_tenant
from app.core.tenancy.models import Tenant, TenantDomain

TENANT_FREE_PATHS = {"/api/health", "/api/docs", "/api/openapi.json", "/api/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in TENANT_FREE_PATHS or not path.startswith("/api"):
            set_current_tenant(None)
            return await call_next(request)

        tenant = await self._resolve_tenant(request)
        if tenant is None:
            return JSONResponse(
                status_code=400,
                content={"detail": "Tenant not found. Provide X-Tenant-ID header or use tenant subdomain."},
            )

        set_current_tenant(TenantContext(tenant=tenant, schema_name=tenant.schema_name))
        response = await call_next(request)
        set_current_tenant(None)
        return response

    async def _resolve_tenant(self, request: Request) -> Tenant | None:
        # 1. Check X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return await self._get_tenant_by_slug(tenant_id)

        # 2. Check subdomain
        host = request.headers.get("host", "")
        subdomain = self._extract_subdomain(host)
        if subdomain:
            return await self._get_tenant_by_slug(subdomain)

        # 3. Check custom domain
        domain = host.split(":")[0]
        return await self._get_tenant_by_domain(domain)

    def _extract_subdomain(self, host: str) -> str | None:
        host_without_port = host.split(":")[0]
        parts = host_without_port.split(".")
        if len(parts) >= 3:
            return parts[0]
        return None

    async def _get_tenant_by_slug(self, slug: str) -> Tenant | None:
        if not re.match(r"^[a-zA-Z0-9_-]+$", slug):
            return None
        async with async_session_factory() as session:
            result = await session.exec(
                select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
            )
            return result.first()

    async def _get_tenant_by_domain(self, domain: str) -> Tenant | None:
        async with async_session_factory() as session:
            result = await session.exec(
                select(TenantDomain).where(TenantDomain.domain == domain)
            )
            tenant_domain = result.first()
            if tenant_domain is None:
                return None

            result = await session.exec(
                select(Tenant).where(Tenant.id == tenant_domain.tenant_id, Tenant.is_active == True)
            )
            return result.first()
```

- [ ] **Step 3: Update `backend/app/main.py` — add middleware and database lifespan**

Replace the entire file:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.core.tenancy.middleware import TenantMiddleware
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting RentManager backend (debug={settings.debug})")
    yield
    await engine.dispose()
    print("Shutting down RentManager backend")


app = FastAPI(
    title="RentManager API",
    version="0.1.0",
    lifespan=lifespan,
    root_path="/api",
)

app.add_middleware(TenantMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/tenancy/context.py backend/app/core/tenancy/middleware.py backend/app/main.py
git commit -m "feat(backend): add tenant resolution middleware with subdomain, header, and domain lookup"
```

---

### Task 8: Celery Skeleton

**Files:**
- Create: `backend/app/celery_app.py`

- [ ] **Step 1: Write `backend/app/celery_app.py`**

```python
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "rentmanager",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.conf.beat_schedule = {}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/celery_app.py
git commit -m "feat(backend): add Celery app skeleton with Redis broker"
```

---

### Task 9: Tests — Health + Tenant Resolution

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/tests/test_tenancy.py`

- [ ] **Step 1: Write `backend/tests/__init__.py`**

Empty file.

- [ ] **Step 2: Write `backend/tests/conftest.py`**

```python
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import get_settings
from app.main import app

settings = get_settings()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def tenant_slug() -> str:
    return f"test-tenant-{uuid.uuid4().hex[:8]}"
```

- [ ] **Step 3: Write `backend/tests/test_health.py`**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_no_tenant_required(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
```

- [ ] **Step 4: Write `backend/tests/test_tenancy.py`**

```python
import uuid

import pytest
from httpx import AsyncClient
from sqlmodel import select

from app.core.tenancy.models import Tenant


@pytest.mark.asyncio
async def test_request_without_tenant_header_to_tenant_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_tenant_slug_rejected(client: AsyncClient):
    response = await client.get(
        "/api/resources",
        headers={"X-Tenant-ID": "'; DROP TABLE tenants;--"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_nonexistent_tenant_returns_400(client: AsyncClient):
    response = await client.get(
        "/api/resources",
        headers={"X-Tenant-ID": "nonexistent-tenant"},
    )
    assert response.status_code == 400
```

- [ ] **Step 5: Run tests locally to verify they pass**

Run:
```bash
docker compose up -d postgres redis meilisearch
docker compose run --rm backend pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "test(backend): add health and tenant resolution tests"
```

---

### Task 10: Full Stack Smoke Test

- [ ] **Step 1: Build and start all services**

```bash
docker compose up -d --build
```

- [ ] **Step 2: Verify all containers are healthy**

```bash
docker compose ps
```

Expected: all 8 services running (postgres, redis, meilisearch, minio, traefik, backend, celery-worker, celery-beat, frontend)

- [ ] **Step 3: Run migration**

```bash
docker compose exec backend alembic upgrade head
```

Expected: Migration 0001 applied successfully

- [ ] **Step 4: Verify backend health**

```bash
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 5: Verify backend through Traefik**

```bash
curl http://localhost/api/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 6: Verify frontend**

```bash
curl -s http://localhost:3000 | head -20
```

Expected: HTML with "RentManager" in the content

- [ ] **Step 7: Verify frontend through Traefik**

```bash
curl -s http://localhost | head -20
```

Expected: HTML from Next.js

- [ ] **Step 8: Verify Meilisearch**

```bash
curl http://localhost:7700/health
```

Expected: `{"status":"available"}`

- [ ] **Step 9: Verify MinIO console is accessible**

Open `http://localhost:9001` in browser. Login with minioadmin / minioadmin_dev.

- [ ] **Step 10: Verify Traefik dashboard**

Open `http://localhost:8080` in browser. Should see Traefik dashboard with backend and frontend routers.

- [ ] **Step 11: Run test suite inside container**

```bash
make test
```

Expected: All tests pass

- [ ] **Step 12: Verify data persists across restarts**

```bash
docker compose down
docker compose up -d
docker compose exec backend alembic current
```

Expected: Shows revision 0001 (data persisted via named volumes)

- [ ] **Step 13: Final commit — verify clean state**

```bash
git status
```

Expected: no uncommitted changes

---

## Post-Plan Notes

### What this plan produces

A fully running development stack with:
- 8 Docker services with health checks and named volumes
- FastAPI backend with tenant-aware middleware
- Next.js 15 frontend with Tailwind CSS v4
- PostgreSQL with public schema tables (tenants, tenant_domains, platform_config)
- Alembic migrations working
- Celery ready for background jobs
- Traefik routing `/api/*` to backend, everything else to frontend
- Test suite with async fixtures

### What comes next

**Plan 2: Auth & RBAC** — user registration, JWT auth, role/permission models, auth middleware, login/signup endpoints.
