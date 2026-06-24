import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rm_mcp.config import BACKEND_DIR, FRONTEND_DIR, INDEX_DIR, INDEX_PATH, PROJECT_ROOT
from rm_mcp.indexer.linker import build_links
from rm_mcp.indexer.python_parser import parse_backend
from rm_mcp.indexer.ts_parser import parse_frontend


def run_reindex(quiet: bool = False) -> dict:
    if not quiet:
        print("Indexing backend...")
    backend = parse_backend(BACKEND_DIR, PROJECT_ROOT)

    if not quiet:
        print("Indexing frontend...")
    frontend = parse_frontend(FRONTEND_DIR, PROJECT_ROOT)

    if not quiet:
        print("Building cross-stack links...")
    links = build_links(backend, frontend)

    index = {
        "version": 1,
        "indexed_at": datetime.now(UTC).isoformat(),
        "backend": backend,
        "frontend": frontend,
        "links": links,
    }

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, default=str))

    if not quiet:
        print(f"Index built: {len(backend['routes'])} routes, "
              f"{len(backend['models'])} models, "
              f"{len(frontend['pages'])} pages, "
              f"{len(frontend['hooks'])} hooks, "
              f"{len(links)} links")
        print(f"Saved to {INDEX_PATH}")

    return index


def load_index() -> dict:
    if not INDEX_PATH.exists():
        return {}
    return json.loads(INDEX_PATH.read_text())


def show_status() -> None:
    if not INDEX_PATH.exists():
        print("No index found. Run: python -m rm_mcp reindex")
        return

    index = load_index()
    indexed_at = index.get("indexed_at", "unknown")
    backend = index.get("backend", {})
    frontend = index.get("frontend", {})
    links = index.get("links", [])

    print(f"Index version: {index.get('version', '?')}")
    print(f"Indexed at:    {indexed_at}")
    print(f"Routes:        {len(backend.get('routes', []))}")
    print(f"Services:      {len(backend.get('services', []))}")
    print(f"Models:        {len(backend.get('models', []))}")
    print(f"Schemas:       {len(backend.get('schemas', []))}")
    print(f"Celery tasks:  {len(backend.get('tasks', []))}")
    print(f"Pages:         {len(frontend.get('pages', []))}")
    print(f"Hooks:         {len(frontend.get('hooks', []))}")
    print(f"Stores:        {len(frontend.get('stores', []))}")
    print(f"Components:    {len(frontend.get('components', []))}")
    print(f"Links:         {len(links)}")
