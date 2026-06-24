def test_list_docs():
    from rm_mcp.docs import list_docs
    docs = list_docs()
    assert len(docs) > 0
    assert any("architecture" in d["topic"] for d in docs)


def test_get_doc():
    from rm_mcp.docs import get_doc
    content = get_doc("architecture-overview")
    assert content is not None
    assert len(content) > 0


def test_get_doc_not_found():
    from rm_mcp.docs import get_doc
    content = get_doc("nonexistent-topic-xyz")
    assert content is None


def test_search_docs():
    from rm_mcp.docs import search_docs
    results = search_docs("booking")
    assert len(results) > 0
