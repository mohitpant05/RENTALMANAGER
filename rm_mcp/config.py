from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend" / "app"
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "src"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
INDEX_DIR = PROJECT_ROOT / ".rm-mcp"
INDEX_PATH = INDEX_DIR / "index.json"

BACKEND_GLOB = "**/*.py"
