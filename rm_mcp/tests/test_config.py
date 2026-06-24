from pathlib import Path

def test_config_paths_exist():
    from rm_mcp.config import PROJECT_ROOT, BACKEND_DIR, FRONTEND_DIR, KNOWLEDGE_DIR, INDEX_PATH

    assert PROJECT_ROOT.is_dir()
    assert BACKEND_DIR == PROJECT_ROOT / "backend" / "app"
    assert FRONTEND_DIR == PROJECT_ROOT / "frontend" / "src"
    assert KNOWLEDGE_DIR == PROJECT_ROOT / "knowledge"
    assert INDEX_PATH == PROJECT_ROOT / ".rm-mcp" / "index.json"
