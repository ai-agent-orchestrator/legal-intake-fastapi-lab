"""B01/B02b: split the synthetic guides, embed them, and publish a new memvid index version.

Real run on the owner's PC (after the one-time pinned download):
  set HF_HUB_OFFLINE=1
  python -m scripts.ingest_guides --embedder e5 --revision <commit-hash> --index-version e5-<date>-v1
Dry run anywhere:
  python -m scripts.ingest_guides --embedder fake --index-version fake-v1 --index-dir data/index-fake
Vectors and .mv2 files stay under data/ (git-ignored). Only counts and IDs go to docs/evidence/.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

from scripts._guards import ATTEMPTS, block_network, scrub_environment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedder", choices=["e5", "fake"], required=True)
    parser.add_argument("--revision")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-seconds", type=float, default=900)
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--index-version", required=True)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--overlap", type=int, default=40)
    parser.add_argument("--evidence", default="docs/evidence/B01/chunks_summary.json")
    args = parser.parse_args()
    scrub_environment()
    block_network()

    from app.rag.corpus import build_chunks, load_guides
    from app.rag.embeddings import make_embedder
    from app.rag.index import publish_index

    embedder = make_embedder(args.embedder, args.revision, args.device, args.batch_size, args.max_seconds)
    docs = load_guides()
    tokenizer_id = f"{embedder.model_id}@{embedder.revision}"
    chunks = build_chunks(docs, embedder.count_tokens, tokenizer_id, args.max_tokens, args.overlap)
    start = time.monotonic()
    vectors = embedder.encode_documents([c.safe_text for c in chunks])
    encode_seconds = time.monotonic() - start
    manifest = publish_index(chunks, vectors, index_dir=Path(args.index_dir), index_version=args.index_version,
                             embedding_model=embedder.model_id, pinned_revision=embedder.revision,
                             dimension=embedder.dimension, normalization=embedder.normalization)
    per_doc = Counter(c.document_id for c in chunks)
    doc_tokens = {d.document_id: embedder.count_tokens(d.text) for d in docs}
    tokens = [c.token_count for c in chunks]
    summary = {
        "embedder": args.embedder, "real_model": args.embedder == "e5",
        "model": embedder.model_id, "revision": embedder.revision, "dimension": embedder.dimension,
        "index_version": manifest.index_version, "index_sha256": manifest.sha256,
        "chunker_version": manifest.chunker_version, "max_tokens": args.max_tokens, "overlap": args.overlap,
        "documents": len(docs), "chunks": len(chunks), "chunks_per_document": dict(sorted(per_doc.items())),
        "document_tokens": doc_tokens,
        "document_tokens_in_600_1200": {k: 600 <= v <= 1200 for k, v in doc_tokens.items()},
        "chunk_tokens": {"min": min(tokens), "max": max(tokens), "median": statistics.median(tokens)},
        "chunk_ids": [c.chunk_id for c in chunks],
        "encode_seconds": round(encode_seconds, 3), "network_attempts": ATTEMPTS,
    }
    out = Path(args.evidence)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("index_version", "chunks", "chunk_tokens", "real_model")},
                     ensure_ascii=False))
    return 0 if not ATTEMPTS else 1


if __name__ == "__main__":
    sys.exit(main())
