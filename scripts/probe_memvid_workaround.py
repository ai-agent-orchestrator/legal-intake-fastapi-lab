"""Approved B02a workaround gate; isolated processes, >=60 synthetic vectors."""
import argparse
import json
import math
import platform
import random
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.rag.offline import offline


def run_case(count, batch):
    from app.rag.index import load_memvid
    with offline():
        sdk = load_memvid()
        directory = ROOT / "data/probes" / uuid4().hex
        directory.mkdir(parents=True)
        rng = random.Random(3)
        vectors = []
        for _ in range(count):
            raw = [rng.gauss(0, 1) for _ in range(1024)]
            norm = math.sqrt(sum(x*x for x in raw))
            vectors.append([x/norm for x in raw])
        records = [{"title": f"chunk-{i:03d}", "label": "synthetic", "text": f"synthetic record {i}",
                    "metadata": {}} for i in range(count)]
        path = directory / "probe.mv2"
        memory = sdk.create(str(path), enable_vec=True, enable_lex=True)
        try:
            for start in range(0, count, batch):
                memory.put_many(records[start:start+batch], embeddings=vectors[start:start+batch],
                                opts={"enable_embedding": False},
                                embedding_identity={"provider": "external", "model": "synthetic-probe-1024"})
            memory.seal()
        finally:
            memory.close()
        memory = sdk.use("basic", str(path), read_only=True, enable_vec=True, enable_lex=True)
        try:
            all_hits = memory.find("", mode="sem", k=count, query_embedding=vectors[0])
            own = []
            for record, vector in zip(records, vectors):
                hits = memory.find("", mode="sem", k=1, query_embedding=vector)["hits"]
                own.append({"chunkId": record["title"], "top1": hits[0]["title"] if hits else None,
                            "pass": bool(hits and hits[0]["title"] == record["title"])})
            return {"count": count, "batch": batch, "totalHits": all_hits.get("total_hits"),
                    "returnedHits": len(all_hits["hits"]), "selfTop1": sum(r["pass"] for r in own),
                    "selfChecks": own,
                    "complete": all_hits.get("total_hits") == count and all(r["pass"] for r in own)}
        finally:
            memory.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.case:
        count, batch = map(int, args.case.split(":"))
        print(json.dumps(run_case(count, batch)))
        return 0
    cases = []
    for count, batch in [(60,60), (60,8), (120,8)]:
        attempts = []
        for attempt in range(2):
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--case", f"{count}:{batch}"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
            attempts.append({"attempt":attempt+1,"exitCode":result.returncode,"error":result.stderr[-2000:] if result.returncode else None})
            if result.returncode == 0:
                break
        if result.returncode:
            cases.append({"count": count, "batch": batch, "complete": False,
                          "executionError": result.stderr[-2000:]})
        else:
            cases.append(json.loads(result.stdout))
        cases[-1]["executionAttempts"] = attempts
    passed = not cases[0]["complete"] and cases[1]["complete"] and cases[2]["complete"] and "executionError" not in cases[0]
    report = {"platform": platform.platform(), "sdk": "2.0.160", "vectorSource": "synthetic random unit vectors, NOT E5",
              "batchLimit": 8, "explicitPutOptions": {"enable_embedding": False},
              "telemetry": "MEMVID_TELEMETRY=0", "pythonSocketsBlocked": True,
              "expectedLargeBatchFailure": not cases[0]["complete"] and "executionError" not in cases[0],
              "cases": cases, "workaroundGatePassed": passed}
    target = ROOT / "docs/evidence/B02a/memvid_workaround_windows.json"
    target.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"workaroundGatePassed": passed,
                      "cases": [{k:r.get(k) for k in ("count","batch","totalHits","selfTop1","executionError")} for r in cases]}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
