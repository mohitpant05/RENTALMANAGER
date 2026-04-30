# FastAPI Request Lifecycle — Express.js Comparison

How a request flows through the RentManager FastAPI backend, mapped to Express.js concepts.

## The Big Picture

| Express.js | FastAPI (this project) |
|------------|----------------------|
| `app.use(middleware)` | `app.add_middleware(TenantMiddleware)` |
| `app.use('/api/auth', authRouter)` | `app.include_router(auth_router)` |
| `req.params`, `req.body` | Pydantic models, path/query params |
| `req.user` (set by middleware) | `Depends(get_current_user)` |
| `req.db` (set by middleware) | `Depends(get_db)` |
| `res.json()` | `return dict` / `response_model` |
| `next()` | `call_next(request)` |
| `asyncLocals` / `cls-hooked` | `contextvars.ContextVar` |

## Full Request Trace: `POST /api/auth/login`

### Step 1: ASGI Server (≈ Node's HTTP server)

Uvicorn receives the TCP connection, parses HTTP, creates an ASGI `scope` dict.

```
Express equivalent: http.createServer() → req, res objects
```

### Step 2: TenantMiddleware (≈ app.use())

```python
# app/core/tenancy/middleware.py
class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 1. Skip tenant-free paths
        if path in TENANT_FREE_PATHS:
            return await call_next(request)  # ← like next() in Express

        # 2. Resolve tenant (header → subdomain → custom domain)
        tenant = await self._resolve_tenant(request)

        # 3. Set tenant in ContextVar (≈ asyncLocalStorage.run())
        set_current_tenant(TenantContext(tenant=tenant, schema_name=...))

        response = await call_next(request)

        # 4. Clean up
        set_current_tenant(None)
        return response
```

**Express equivalent:**

```javascript
app.use(async (req, res, next) => {
  const tenant = await resolveTenant(req.headers['x-tenant-id']);
  req.tenant = tenant;  // Express mutates req
  next();
});
```

Key difference: Express mutates `req`. FastAPI uses `ContextVar` — a thread/task-local variable that any function in the call stack can read without it being passed as an argument. Similar to Node's `AsyncLocalStorage`.

### Step 3: Router Resolution (≈ app.use('/path', router))

FastAPI matches the path and method to a route handler:

```python
# app/core/auth/router.py
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,                    # ← request body, auto-validated
    session: AsyncSession = Depends(get_db),  # ← dependency injection
):
    ...
```

**Express equivalent:**

```javascript
const router = express.Router();
router.post('/login', async (req, res) => {
  const data = req.body;  // no auto-validation
  const session = req.db; // set by middleware
});
app.use('/api/auth', router);
```

### Step 4: Dependency Injection (≈ middleware, but per-route)

This is where FastAPI diverges most from Express. Instead of middleware setting `req.db`, FastAPI uses `Depends()`:

```python
# app/database.py
async def get_db():
    tenant_ctx = get_current_tenant()  # ← reads ContextVar set by middleware
    async with async_session_factory() as session:
        # Set PostgreSQL search_path to tenant's schema
        await session.execute(
            text(f"SET search_path TO {tenant_ctx.schema_name}, public")
        )
        yield session                   # ← "yield" means cleanup runs after handler
        await session.execute(text("SET search_path TO public"))
```

**Express equivalent (conceptual):**

```javascript
// In Express, you'd do this in middleware:
app.use(async (req, res, next) => {
  const pool = getPool();
  const conn = await pool.getConnection();
  await conn.query(`SET search_path TO ${req.tenant.schema}`);
  req.db = conn;
  next();
  conn.release();  // cleanup — but Express doesn't guarantee this runs
});
```

FastAPI's `yield` in a dependency = guaranteed cleanup. Express needs `res.on('finish')` or try/finally.

### Step 5: Request Body Validation (≈ joi/zod middleware)

```python
# app/core/auth/schemas.py
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

FastAPI auto-parses JSON body and validates against the Pydantic model. Invalid → 422 response. No manual `req.body` parsing.

**Express equivalent:**

```javascript
// You'd add validation middleware manually:
router.post('/login', validate(loginSchema), handler);
```

### Step 6: Handler Execution

```python
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_db)):
    tenant_ctx = get_current_tenant()
    tenant_id = str(tenant_ctx.tenant.id)
    user = await authenticate_user(session, data)      # verify credentials
    roles = await get_user_roles(session, str(user.id)) # load RBAC roles
    return await create_tokens(user, tenant_id, roles)  # JWT creation
```

Return value is auto-serialized to JSON via `response_model=TokenResponse`. No `res.json()` needed.

### Step 7: Response Serialization

FastAPI takes the return value, validates it against `response_model` (strips extra fields), serializes to JSON, sets `Content-Type: application/json`.

**Express equivalent:** `res.json(data)` — but no output validation.

## Dependency Chain Visualization

For a protected endpoint like `GET /api/auth/me`:

```
Request arrives
  │
  ├── TenantMiddleware.dispatch()
  │     └── set_current_tenant(ctx)      ← ContextVar
  │
  ├── FastAPI resolves dependencies:
  │     ├── get_db()
  │     │     └── reads ContextVar → SET search_path
  │     │
  │     └── get_current_user()
  │           ├── HTTPBearer() → extracts token from Authorization header
  │           ├── decode_token() → validates JWT signature + expiry
  │           ├── get_current_tenant() → reads ContextVar, checks tenant_id matches
  │           └── SELECT user WHERE id = token.sub
  │
  ├── Handler runs with (user, session) already resolved
  │
  └── Response serialized via response_model
```

In Express, this would be a chain of middleware:

```javascript
router.get('/me',
  extractTenant,      // ← middleware
  attachDb,           // ← middleware
  requireAuth,        // ← middleware
  async (req, res) => {
    // req.tenant, req.db, req.user all set by middleware
    res.json(req.user);
  }
);
```

## Auth Dependencies — The Permission System

```python
# Protect an endpoint:
@router.get("/resources", dependencies=[Depends(require_permission("resources:own:read"))])
async def list_resources(...):
    ...
```

`require_permission("resources:own:read")` returns a dependency function that:
1. Calls `get_current_user()` (which calls `get_db()`)
2. Loads user's role permissions from DB
3. Checks wildcard matching: `resources:*:read`, `resources:own:*`, `*:*:*`
4. Returns user or raises 403

**Express equivalent:**

```javascript
router.get('/resources',
  requireAuth,
  requirePermission('resources:own:read'),
  handler
);
```

Same concept, but Express passes through `next()` chain. FastAPI composes via `Depends()` — dependencies can depend on other dependencies, forming a DAG (directed acyclic graph) that FastAPI resolves automatically.

## Error Handling

| Express | FastAPI |
|---------|---------|
| `next(err)` / error middleware | `raise HTTPException(status_code=400, detail="...")` |
| Custom error class + handler | Exception handlers: `@app.exception_handler(CustomError)` |
| `res.status(404).json(...)` | `raise HTTPException(404, detail="Not found")` |

FastAPI catches `HTTPException` anywhere in the call stack — no need to pass errors up through callbacks or `next()`.

## Key Differences Summary

| Concept | Express | FastAPI |
|---------|---------|---------|
| **Middleware** | `app.use(fn)`, runs on every request | `app.add_middleware(Class)`, same |
| **Per-route deps** | Middleware array on route | `Depends()` in function signature |
| **Request data** | `req.body`, `req.params`, `req.query` | Type-annotated function params, auto-parsed |
| **Validation** | Manual (joi/zod) | Built-in (Pydantic) |
| **DB session** | `req.db` via middleware | `Depends(get_db)` with yield cleanup |
| **Tenant context** | `req.tenant` (mutate req) | `ContextVar` (async-safe, implicit) |
| **Auth** | Passport.js middleware | `Depends(get_current_user)` |
| **Response** | `res.json(data)` | `return data` + `response_model` |
| **Async** | Callback / async middleware | Native `async def` everywhere |
| **Cleanup** | `res.on('finish')` | `yield` in dependency (guaranteed) |

## ASGI vs Express Middleware Order

Both execute middleware in order of registration, but ASGI middleware wraps (onion model):

```
Express (linear):     middleware1 → middleware2 → handler → response
ASGI (onion):         middleware1.before → middleware2.before → handler
                      middleware2.after ← middleware1.after ← response
```

ASGI middleware sees both the request (before `call_next`) and the response (after `call_next`). Express middleware only sees the request unless you hook into `res.on('finish')`.
