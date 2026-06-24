import json


def test_run_reindex_creates_index():
    from rm_mcp.indexer.pipeline import run_reindex, load_index
    from rm_mcp.config import INDEX_PATH

    run_reindex(quiet=True)

    assert INDEX_PATH.exists()
    index = load_index()

    assert index["version"] == 1
    assert "indexed_at" in index
    assert len(index["backend"]["routes"]) > 0
    assert len(index["backend"]["models"]) > 0
    assert len(index["frontend"]["pages"]) > 0
    assert len(index["frontend"]["hooks"]) > 0
    assert isinstance(index["links"], list)
