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

# Frontend Dev Rules

## React Hooks — Never Violate Call Order

**Rule**: ALL hooks (`useState`, `useEffect`, `useQuery`, `useMutation`, `useForm`, `usePermissions`, etc.) MUST be called before ANY conditional return. No exceptions.

**Why**: React tracks hooks by call index. An early return that skips hooks causes "Rendered fewer hooks than expected" hydration crash.

```tsx
// BAD — hooks after early return
function Page() {
  const { hasPermission, isLoading } = usePermissions();
  if (isLoading) return <Spinner />;           // early return
  if (!hasPermission("x")) return null;        // early return
  const [open, setOpen] = useState(false);     // CRASH — skipped on some renders
  const { data } = useQuery({ ... });          // CRASH
}

// GOOD — all hooks first, guards after
function Page() {
  const { hasPermission, isLoading } = usePermissions();
  const [open, setOpen] = useState(false);
  const { data } = useQuery({ ... });

  if (isLoading) return <Spinner />;
  if (!hasPermission("x")) { router.replace("/admin"); return null; }

  return <div>...</div>;
}
```

**Past incidents**: 6 admin pages had this bug (staff, roles, settings, payments, email, commission).

## HTML Nesting — No `<button>` Inside `<button>`

**Rule**: Never wrap `<Button>` inside `<DropdownMenuTrigger>` or any component that renders a `<button>`. Use the `render` prop instead.

```tsx
// BAD — nested buttons, hydration error
<DropdownMenuTrigger>
  <Button variant="ghost"><MoreVertical /></Button>
</DropdownMenuTrigger>

// GOOD — render prop avoids nesting
<DropdownMenuTrigger render={<Button variant="ghost" size="icon" />}>
  <MoreVertical />
</DropdownMenuTrigger>
```

## ACL Permission Gating on UI

**Rule**: Action buttons (create, edit, delete, status change) must be wrapped in `hasPermission()` checks. Navigation is filtered by `canAccessNav()` in the icon rail — but action buttons within pages need explicit gating.

**Pattern**:
```tsx
const { hasPermission } = usePermissions();

{hasPermission("bookings:*:confirm") && (
  <Button onClick={handleConfirm}>Confirm</Button>
)}
```

Backend enforces permissions too, but hiding buttons prevents confusing 403 errors for users.

## Admin/Staff Route Protection

**Rule**: Admin and staff users must never land on public-facing pages (`/browse`, `/profile`). Redirect them to `/admin`. Customer-facing pages should check `user.user_type` and redirect accordingly.

**Rule**: When redirecting based on auth state, never put the early return before hooks that run later in the component. Use the pattern above (hooks first, redirect guard after).

## No `router.replace()` During Render

**Rule**: Never call `router.replace()` or `router.push()` directly in the render body. It triggers React's "Cannot update component while rendering" error. Always wrap in `useEffect`.

```tsx
// BAD — setState during render
if (!hasPermission("x")) { router.replace("/admin"); return null; }

// GOOD — redirect in useEffect, return spinner inline
const denied = !permsLoading && !hasPermission("x");
useEffect(() => { if (denied) router.replace("/admin"); }, [denied, router]);
if (permsLoading || denied) return <Spinner />;
```

## Permission Bypass — Admin Only

**Rule**: Only `user_type === "admin"` bypasses permission checks. Staff must always be checked against their actual permissions. Never use `isAdmin()` from auth-store for permission bypass — it returns true for both admin AND staff.

**Past incident**: `usePermissions` hook used `isAdmin()` which returned true for staff, giving staff god-mode access to all pages and actions.

## Theme CSS Injection

**Rule**: Never use `document.documentElement.style.setProperty()` for theme variables. It creates inline styles with highest specificity that override `.dark` class rules, breaking dark/light toggle.

**Correct approach**: Inject a `<style>` tag with `:root {}` and `.dark {}` blocks. This respects CSS cascade and allows dark mode toggle to work.

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
