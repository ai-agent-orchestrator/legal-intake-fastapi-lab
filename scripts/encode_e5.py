"""Isolated offline E5 worker. Parent terminates this process on wall timeout."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.rag.offline import offline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["documents","compare","confirm"],required=True)
    parser.add_argument("--batch",type=int,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    with offline():
        import numpy as np
        from app.rag.corpus import chunk_guides, load_guides, make_query, query_input
        from app.rag.embeddings import E5Embedder
        started = time.perf_counter()
        embedder = E5Embedder()
        loading = time.perf_counter()-started
        if args.phase == "documents":
            chunks = chunk_guides(load_guides(), embedder.tokenizer, "e5-v1")
            texts = [c.text for c in chunks]
            ids = [c.metadata["chunkId"] for c in chunks]
        else:
            records = json.loads((ROOT/"fixtures/rag/evaluation.json").read_text(encoding="utf-8"))
            split = "holdout" if args.phase == "confirm" else "compare"
            records = [r for r in records if r["split"] == split]
            texts = [make_query(r["intake"]) for r in records]
            ids = [r["questionId"] for r in records]
        if args.phase == "documents":
            vectors, report = embedder.encode(texts,queries=False,batch_size=args.batch)
        else:
            singles, timings = [], []
            for text in texts:
                matrix, timing = embedder.encode([text],queries=True,batch_size=1)
                singles.append(matrix[0])
                timings.append(timing["encodeSeconds"]*1000)
            vectors = np.asarray(singles)
            report = {**timing,"count":len(texts),"encodeSeconds":sum(timings)/1000,
                      "maxFinalTokens":max(len(embedder.tokenizer.encode(query_input(t))) for t in texts),
                      "individualQueryEmbeddingMs":timings,"meanEmbeddingMs":sum(timings)/len(timings)}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        np.save(args.output,vectors)
        report.update(phase=args.phase, ids=ids, loadSeconds=loading,
                      offline=True, pythonSocketsBlocked=True)
        args.output.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
