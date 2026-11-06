"""Recalculate B01 evidence from checked-in sources, never serialize vectors."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["MEMVID_TELEMETRY"] = "0"
from app.rag.corpus import chunk_guides, load_guides, load_tokenizer, make_query, model_config, query_input


def main():
    tokenizer = load_tokenizer()
    guides = load_guides()
    chunks = chunk_guides(guides, tokenizer)
    file = ROOT / "fixtures/rag/evaluation.json"
    evaluation = json.loads(file.read_text(encoding="utf-8"))
    report = {
        "actualTokenizer": model_config(), "offline": True, "weightsLoaded": False,
        "documents": [{"documentId": g["documentId"], "caseType": g["caseType"],
                       "tokens": len(tokenizer.encode(g["text"])),
                       "sha256": hashlib.sha256(g["text"].encode()).hexdigest()} for g in guides],
        "caseCounts": dict(Counter(g["caseType"] for g in guides)),
        "chunkCount": len(chunks), "maxChunkTokens": max(c.metadata["tokenCount"] for c in chunks),
        "chunksPerDocument": dict(Counter(c.metadata["documentId"] for c in chunks)),
        "chunkMetadataFields": sorted(chunks[0].metadata),
        "maxFinalQueryTokens": max(len(tokenizer.encode(query_input(make_query(r["intake"])))) for r in evaluation),
        "evaluationSha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        "splits": {split: {"count": sum(r["split"] == split for r in evaluation),
            "evidence": sum(r["split"] == split and bool(r["expectedDocumentIds"]) for r in evaluation),
            "noEvidence": sum(r["split"] == split and not r["expectedDocumentIds"] for r in evaluation)}
            for split in ("compare", "holdout")},
    }
    target = ROOT / "docs/evidence/B01/corpus_manifest.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
