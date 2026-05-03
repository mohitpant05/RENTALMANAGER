<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **RENTALMANAGER** (2586 symbols, 3475 relationships, 5 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/RENTALMANAGER/context` | Codebase overview, check index freshness |
| `gitnexus://repo/RENTALMANAGER/clusters` | All functional areas |
| `gitnexus://repo/RENTALMANAGER/processes` | All execution flows |
| `gitnexus://repo/RENTALMANAGER/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

# Project Structure

- `backend/` — FastAPI + SQLModel + Celery (Python 3.12, `uv` package manager)
- `frontend/` — Next.js 15 + React 19 + Tailwind CSS 4 (no test framework configured)

# Backend

## Setup
```bash
cd backend && uv pip install --system ".[dev]"
```

## Commands
| Task | Command |
|------|---------|
| Lint | `cd backend && ruff check .` |
| Test (all) | `cd backend && pytest --tb=short -q` |
| Test (single) | `cd backend && pytest tests/test_auth_unit.py -v` |
| Migrate | `docker compose exec backend alembic upgrade head` |
| New migration | `docker compose exec backend alembic revision --autogenerate -m "message"` |

## Testing Prerequisites
Integration tests need: postgres, redis, meilisearch, minio. CI runs them as services (see `.github/workflows/ci.yml`). Local: `make up` then `cd backend && pytest`.

## Notes
- `asyncio_mode = "auto"` in pytest config — no `@pytest.mark.asyncio` needed
- Multi-tenant: tenant resolution via `app/core/tenancy/middleware.py`
- Celery worker + beat run as separate deployments (see deploy.yml)
- Code in `app/` only (hatchling wheel target)

## Test Credentials

To create a test user for local development:

```bash
# Option 1: Using docker compose (recommended)
docker compose exec backend python -c "
import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from uuid import uuid4
import bcrypt
from app.core.auth.models import User

async def create():
    engine = create_async_engine('postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager')
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == 'test@rentmanager.dev'))
        if result.first():
            print('User exists: test@rentmanager.dev / testpassword123')
            return
        user = User(
            id=uuid4(), email='test@rentmanager.dev',
            password_hash=bcrypt.hashpw('testpassword123'.encode(), bcrypt.gensalt()).decode(),
            full_name='Test User', is_active=True, is_verified=True, user_type='admin'
        )
        session.add(user)
        await session.commit()
        print('Created: test@rentmanager.dev / testpassword123')
    await engine.dispose()

asyncio.run(create())
"

# Option 2: Direct script (requires services running)
cd backend && python scripts/create_test_user.py
```

Login at: `http://localhost:3000/login`

**Current test credentials:**
- Email: `test@rentmanager.dev`
- Password: `testpassword123`
- Role: `admin` (full access)

# Frontend

## Commands
| Task | Command |
|------|---------|
| Dev | `cd frontend && npm run dev` (uses Turbopack) |
| Build | `cd frontend && npm run build` |
| Lint | `cd frontend && npm run lint` |

## Notes
- Import alias: `@/*` maps to `frontend/src/*` (tsconfig paths)
- Tailwind CSS v4 (not v3) with `@tailwindcss/postcss`
- shadcn v4 + `class-variance-authority` for component variants
- No test runner configured

# Docker & Deploy

- `make up` / `make down` — docker compose wrappers
- `make test` — runs pytest inside backend container
- Deploy: pushes to ECR, updates k3s via kubectl (see `.github/workflows/deploy.yml`)
- Two compose files: `docker-compose.yml` (dev), `docker-compose.prod.yml`
