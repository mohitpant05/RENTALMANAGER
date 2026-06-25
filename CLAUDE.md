# Git Workflow

- **NEVER push directly to `live` or `main`.** Always create a feature branch, push there, create a PR, then merge.
- Branch naming: `feat/short-name`, `fix/short-name`, `docs/short-name`
- Flow: `git checkout -b feat/x origin/live` → commit → push → PR → merge

# MCP Tools — Code Intelligence

This project has two MCP servers: **rm** (project-specific) and **gitnexus** (graph-based). Use the right tool for the job.

## RM MCP (Project-Specific) — Use First

Purpose-built for this codebase. Faster and more accurate for structural questions.

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

## GitNexus (Graph-Based) — Use for Impact & Flows

Best for understanding call chains, blast radius, and safe refactoring.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

| Tool | When to use |
|------|-------------|
| `gitnexus_impact({target: "symbolName"})` | Blast radius before editing a symbol |
| `gitnexus_detect_changes()` | Verify affected scope before committing |
| `gitnexus_context({name: "symbolName"})` | 360-degree view: callers, callees, flows |
| `gitnexus_query({query: "concept"})` | Find execution flows for a concept |
| `gitnexus_rename({...})` | Rename symbols across call graph |

### Always Do

- **Run `gitnexus_impact` before editing any symbol** — report blast radius (callers, affected processes, risk level)
- **Run `gitnexus_detect_changes()` before committing** — verify changes only affect expected scope
- **Warn the user** if impact analysis returns HIGH or CRITICAL risk

### Never Do

- NEVER edit a function/class/method without first running `gitnexus_impact`
- NEVER ignore HIGH or CRITICAL risk warnings
- NEVER rename symbols with find-and-replace — use `gitnexus_rename`

### Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/RENTALMANAGER/context` | Codebase overview, index freshness |
| `gitnexus://repo/RENTALMANAGER/clusters` | All functional areas |
| `gitnexus://repo/RENTALMANAGER/processes` | All execution flows |
| `gitnexus://repo/RENTALMANAGER/process/{name}` | Step-by-step execution trace |

### Skills

| Task | Skill file |
|------|------------|
| Architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

## Decision Guide

| Question | Use |
|----------|-----|
| "What routes/pages/models exist?" | **RM MCP** |
| "Trace feature end-to-end" | **RM MCP** `trace_flow` |
| "What breaks if I change X?" | **GitNexus** `impact` |
| "Find all callers of X" | **GitNexus** `context` |
| "Rename symbol safely" | **GitNexus** `rename` |
| "Search for concept across codebase" | **RM MCP** `query` first, then GitNexus if need flow-level detail |

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **RENTALMANAGER** (6339 symbols, 9660 relationships, 130 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
