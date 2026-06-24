# RM-MCP: RentalManager Code Intelligence MCP Server

## Overview

A custom MCP (Model Context Protocol) server that provides structured codebase context for the RentalManager project. Parses both Python backend and TypeScript frontend via AST analysis, builds a cross-stack knowledge graph, and serves it through MCP tools and resources. Eliminates the need for grep-based exploration during AI-assisted development.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 rm-mcp server                    │
│              (Python, stdio MCP)                 │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Indexer   │  │ Query    │  │ Doc Loader   │  │
│  │ Pipeline  │  │ Engine   │  │              │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │           │
│  ┌────▼─────┐  ┌────▼─────┐  ┌──────▼───────┐  │
│  │ Python   │  │ Index    │  │ knowledge/   │  │
│  │ AST      │  │ JSON     │  │ markdown     │  │
│  │ Parser   │  │ Store    │  │ files        │  │
│  ├──────────┤  └──────────┘  └──────────────┘  │
│  │ TS       │                                    │
│  │ TreeSit  │                                    │
│  │ Parser   │                                    │
│  └──────────┘                                    │
└─────────────────────────────────────────────────┘
         ▲
         │ stdio (MCP protocol)
         ▼
    Claude Code / AI client
```

### Components

- **Indexer Pipeline** — parses backend Python + frontend TypeScript, builds structured JSON index
- **Query Engine** — handles MCP tool calls, searches index + docs
- **Doc Loader** — serves `knowledge/` markdown files as MCP resources
- **Index JSON Store** — single `.rm-mcp/index.json` file, regenerated on reindex

## Indexer Extraction

### Backend (Python stdlib `ast` module)

| What | How | Example |
|------|-----|---------|
| API Routes | Parse `@router.get/post/put/delete` decorators | `POST /api/v1/{tenant}/bookings` → `bookings/router.py:create_booking` |
| Service functions | Parse function defs in `**/service.py` | `bookings/service.py:create_booking()` — params, return type |
| SQLAlchemy Models | Parse classes inheriting from `Base` | `Booking` model — columns, relationships, table name |
| Pydantic Schemas | Parse `BaseModel` subclasses | `BookingCreate`, `BookingResponse` — fields + types |
| Celery Tasks | Parse `@celery_app.task` decorators | `send_booking_confirmation_email` |
| Dependencies | Parse `Depends()` in route signatures | Auth deps, DB session, tenant resolution |
| Route→Service→Model chain | Trace function calls within each module | `router.create_booking → service.create_booking → Booking model` |

### Frontend (regex-based TypeScript parser)

> **Implementation note:** The spec originally called for tree-sitter as the TypeScript parser. In practice, regex-based scanning was chosen instead — it avoids a native dependency, keeps the install simple, and is sufficient for the structured patterns used in this codebase (page files, hook files, `api.get/post` call sites). tree-sitter would offer more robust parsing but was deemed unnecessary overhead for the current scope.

| What | How | Example |
|------|-----|---------|
| Pages | Scan `app/**/page.tsx` files | `/admin/bookings` → `app/admin/bookings/page.tsx` |
| API calls | Find `api.get/post/put/delete()` patterns (regex) | `api.post('/bookings', data)` in `use-booking-flow.ts` |
| Custom hooks | Parse `hooks/use-*.ts` exports | `useBookingFlow` — what API calls it makes |
| Stores | Parse zustand/store files in `lib/` | `auth-store.ts`, `tenant-store.ts` |
| Components | Parse component exports from `components/` | Which components each page uses |
| Page→Hook→API mapping | Trace imports | `admin/bookings/page.tsx` → `useBookingFlow` → `POST /api/bookings` |

### Cross-stack Linking

The indexer matches frontend API calls to backend routes by URL pattern, producing full traces:

```
admin/bookings/page.tsx
  → useBookingFlow hook
    → POST /api/v1/{tenant}/bookings
      → bookings/router.py:create_booking
        → bookings/service.py:create_booking
          → Booking model (DB)
```

## MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `trace_flow` | Full path from page/route to DB | `trace_flow({from: "admin/bookings"})` |
| `list_routes` | All backend API routes with methods, auth | `list_routes({module: "bookings"})` |
| `list_pages` | All frontend pages with hooks/API calls | `list_pages({area: "admin"})` |
| `find_symbol` | Find function/class/model by name | `find_symbol({name: "create_booking"})` |
| `query` | Fuzzy search across routes, functions, models, docs | `query({q: "payment processing"})` |
| `get_schema` | Get Pydantic schema or SQLAlchemy model details | `get_schema({name: "Booking"})` |
| `get_doc` | Get specific knowledge doc content | `get_doc({topic: "booking-state-machine"})` |
| `overview` | Project summary: modules, route counts, page counts | `overview()` |

## MCP Resources

| Resource URI | Content |
|-------------|---------|
| `rm://overview` | Project summary — module list, route count, page count |
| `rm://routes` | Complete API route table |
| `rm://pages` | Complete page→endpoint mapping |
| `rm://docs/{topic}` | Individual knowledge doc |
| `rm://index-status` | Index age, file counts, staleness |

## Data Model

Index stored at `.rm-mcp/index.json` (gitignored). Structure:

```json
{
  "version": 1,
  "indexed_at": "ISO timestamp",
  "backend": {
    "routes": [{
      "method": "POST",
      "path": "/api/v1/{tenant}/bookings",
      "handler": "create_booking",
      "file": "backend/app/domains/bookings/router.py",
      "line": 45,
      "service_calls": ["bookings.service.create_booking"],
      "auth_required": true,
      "dependencies": ["get_current_user", "get_db"]
    }],
    "services": [{
      "name": "create_booking",
      "module": "bookings",
      "file": "backend/app/domains/bookings/service.py",
      "line": 23,
      "params": [{"name": "db", "type": "Session"}],
      "models_used": ["Booking"],
      "calls": ["send_booking_email.delay"]
    }],
    "models": [{
      "name": "Booking",
      "table": "bookings",
      "file": "backend/app/domains/bookings/models.py",
      "line": 12,
      "columns": [{"name": "id", "type": "UUID"}],
      "relationships": ["resource", "user", "payments"]
    }],
    "schemas": [],
    "tasks": []
  },
  "frontend": {
    "pages": [{
      "route": "/admin/bookings",
      "file": "frontend/src/app/admin/bookings/page.tsx",
      "hooks_used": ["useBookingFlow"],
      "components_used": ["BookingTable"],
      "api_calls": []
    }],
    "hooks": [{
      "name": "useBookingFlow",
      "file": "frontend/src/hooks/use-booking-flow.ts",
      "api_calls": [{"method": "POST", "path": "/bookings", "line": 34}],
      "stores_used": ["auth-store"]
    }],
    "stores": [],
    "components": []
  },
  "links": [{
    "page": "/admin/bookings",
    "hook": "useBookingFlow",
    "api_path": "POST /api/v1/{tenant}/bookings",
    "handler": "bookings.router.create_booking",
    "service": "bookings.service.create_booking",
    "model": "Booking"
  }]
}
```

## File Structure

```
mcp/
├── __init__.py
├── __main__.py          # entry: python -m rm_mcp serve | reindex | status
├── server.py            # MCP server setup, tool/resource handlers
├── indexer/
│   ├── __init__.py
│   ├── pipeline.py      # orchestrates full reindex
│   ├── python_parser.py # AST extraction for backend
│   ├── ts_parser.py     # tree-sitter extraction for frontend
│   └── linker.py        # matches frontend API calls → backend routes
├── query.py             # search/filter/trace logic over index
├── docs.py              # loads knowledge/ markdown files
└── config.py            # paths, patterns to include/exclude
```

## Git Hook Integration

Post-commit hook at `.git/hooks/post-commit`:

```bash
#!/bin/sh
python -m rm_mcp reindex --quiet &
```

Runs reindex in background after each commit. Does not block commits.

## MCP Registration

Added to `.mcp.json`:

```json
{
  "rm": {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "rm_mcp", "serve"],
    "cwd": "/Users/mohit.pant/PERSONAL/RM"
  }
}
```

## CLI Commands

| Command | What it does |
|---------|-------------|
| `python -m rm_mcp serve` | Start MCP server (stdio) |
| `python -m rm_mcp reindex` | Full reindex |
| `python -m rm_mcp reindex --quick` | Only reindex changed files (git diff) |
| `python -m rm_mcp status` | Show index age, file counts, staleness |

## Dependencies

- `mcp` — MCP Python SDK (official Anthropic package)
- `tree-sitter` + `tree-sitter-typescript` — TS/TSX parsing
- Python stdlib `ast` — Python parsing (no extra dep)

No external services, no API keys, no database.

## Future Enhancements (not in scope)

- Vector embeddings for semantic Q&A (ChromaDB + sentence-transformers)
- File watcher for real-time incremental reindex
- Web UI for browsing the knowledge graph
