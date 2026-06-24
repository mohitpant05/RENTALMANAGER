import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m rm_mcp <serve|reindex|status>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "serve":
        from rm_mcp.server import serve
        serve()
    elif command == "reindex":
        quiet = "--quiet" in sys.argv
        from rm_mcp.indexer.pipeline import run_reindex
        run_reindex(quiet=quiet)
    elif command == "status":
        from rm_mcp.indexer.pipeline import show_status
        show_status()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
