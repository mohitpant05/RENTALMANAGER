# Git Workflow

- **NEVER push directly to `live` or `main`.** Always create a feature branch, push there, create a PR, then merge.
- Branch naming: `feat/short-name`, `fix/short-name`, `docs/short-name`

## Feature Branch Lifecycle

Every feature follows this exact flow:

1. **Branch**: `git checkout -b feat/x origin/live`
2. **Build**: Implement the feature, commit to the branch
3. **Deploy**: `docker compose restart backend-dev` (code is volume-mounted) + run migrations if needed
4. **Test**: Verify on backend-dev (:8080) — user tests frontend locally
5. **Push**: `git push -u origin feat/x`
6. **Wait**: Do NOT merge until user says "merge"
7. **Merge**: When user says merge:
   - Create PR against `live` via `gh pr create`
   - Merge PR via `gh pr merge`
   - Sync: `git checkout live && git pull origin live`
   - Deploy live: `docker compose restart backend-prod` + run migrations
   - Update knowledge base if needed
8. **Cleanup**: Delete feature branch locally and remotely

## Local Dev Setup

When user runs frontend locally (outside Docker):

```bash
# Kill any stale local backend on :8000
lsof -i :8000 -P -n  # check first

# Start frontend pointing to backend-dev via Traefik
cd frontend
BACKEND_INTERNAL_URL=http://localhost:8080 npm run dev -- -p 3001
```

- Frontend: `http://localhost:3001`
- API proxy: `:3001/api/*` → Traefik `:8080` → backend-dev container
- SuperAdmin: `http://localhost:3001/superadmin/[secretKey]/...`
- Never run a local Python backend — always use Docker backend-dev

## Rules

- Never commit directly to `live` or `main`
- Always deploy to backend-dev first for testing before merging
- Wait for explicit user approval before merging to live
- Run `alembic upgrade head` inside the container after any migration changes: `docker compose exec backend-dev sh -c "cd /app && PYTHONPATH=/app alembic upgrade head"`
- After merging to live, sync both dev and prod deployments
- When starting frontend locally, always set `BACKEND_INTERNAL_URL=http://localhost:8080`

# MCP Tools — Code Intelligence

This project uses **RM MCP** — a purpose-built MCP server for this codebase.

## RM MCP (Project-Specific)

| Tool | When to use | Example |
|------|-------------|---------|
| `rm__overview` | Project stats, module counts, freshness | Starting a session, orientation |
| `rm__list_routes` | All API routes with handlers, auth, deps | "What endpoints exist for bookings?" |
| `rm__list_pages` | Frontend pages with hooks and API calls | "What pages are in the admin area?" |
| `rm__find_symbol` | Find function/class/model by name | "Where is create_booking defined?" |
| `rm__get_schema` | Model/schema fields, types, relationships | "What fields does Booking have?" |
| `rm__get_doc` | Knowledge docs by topic | "How does auth work?" |
| `rm__query` | Fuzzy search across everything | "payment processing" |
| `rm__trace_flow` | Full path: page → API → service → model | "Trace admin/bookings end to end" |

### When to prefer RM MCP over grep/read

- **Routes**: `rm__list_routes(module="bookings")` beats `grep "APIRouter"` — gives handler, auth, service calls in one shot
- **Pages**: `rm__list_pages(area="admin")` beats scanning `frontend/src/app/` — gives hooks and API deps
- **Schemas**: `rm__get_schema(name="Booking")` beats reading models.py — gives fields, types, relationships
- **Tracing**: `rm__trace_flow(from_identifier="admin/bookings")` beats manual file hopping — full stack trace
- **Search**: `rm__query(q="commission")` for cross-cutting concerns spanning frontend + backend
