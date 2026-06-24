from rm_mcp.config import KNOWLEDGE_DIR


def list_docs() -> list[dict]:
    docs = []
    if not KNOWLEDGE_DIR.exists():
        return docs
    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        topic = md_file.stem
        first_line = ""
        with open(md_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    first_line = line[:120]
                    break
                elif line.startswith("# "):
                    first_line = line[2:].strip()
                    break
        docs.append({
            "topic": topic,
            "file": md_file.name,
            "title": first_line,
        })
    return docs


def get_doc(topic: str) -> str | None:
    if ".." in topic or "/" in topic:
        return None
    md_file = KNOWLEDGE_DIR / f"{topic}.md"
    if md_file.exists():
        return md_file.read_text()

    # Try partial match
    if KNOWLEDGE_DIR.exists():
        for f in KNOWLEDGE_DIR.glob("*.md"):
            if topic.lower() in f.stem.lower():
                return f.read_text()

    return None


def search_docs(q: str) -> list[dict]:
    results = []
    q_lower = q.lower()
    terms = q_lower.split()

    if not KNOWLEDGE_DIR.exists():
        return results

    for md_file in KNOWLEDGE_DIR.glob("*.md"):
        content = md_file.read_text()
        content_lower = content.lower()
        score = sum(content_lower.count(t) for t in terms)
        if score > 0:
            # Extract first matching paragraph
            snippet = ""
            for para in content.split("\n\n"):
                if any(t in para.lower() for t in terms):
                    snippet = para.strip()[:200]
                    break
            results.append({
                "topic": md_file.stem,
                "score": score,
                "snippet": snippet,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:10]
