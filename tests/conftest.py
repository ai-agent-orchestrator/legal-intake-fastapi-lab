def pytest_configure(config):
    # Registered here (not pyproject.toml) to avoid touching a file with local, uncommitted edits.
    config.addinivalue_line("markers", "rag_memvid: needs memvid-sdk; run in the RAG runtime, never skipped silently")
