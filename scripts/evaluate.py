"""B02b: keyword (memvid lex) vs vector retrieval on the synthetic intake set.

  set HF_HUB_OFFLINE=1
  python -m scripts.evaluate --embedder e5 --revision <commit-hash>

Steps: (1) retrieve top-10 chunks per item for both modes, (2) Hit@3 on items that have
evidence (raw ranking, before any gate), (3) calibrate the relevance rule on the compare split
only, (4) apply the frozen rule once to the confirm split. Writes docs/evidence/B02b/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from scripts._guards import ATTEMPTS, block_network, scrub_environment

EVAL_FILE = Path("corpus/synthetic/eval/intakes.json")
RANDOM_BASELINE = {"value": 3 / 10, "assumption": "10 documents, 1 gold document, 3 distinct documents drawn"}


def query_for(intake: dict) -> str:
    from app.rag.masking import mask_pii
    from app.rag.schemas import build_query
    step = intake.get("desiredNextStep")
    return build_query(intake["caseType"], mask_pii(intake["coreStatement"]), mask_pii(step) if step else None)


def calibrate(rows: list[dict], mode: str) -> dict:
    """Pick (tau_abs, tau_gap): no compare no-evidence item may pass the gate; then minimise
    evidence items wrongly gated out; ties go to the more conservative (higher) thresholds."""
    tops = sorted({r[mode]["top1"] for r in rows} | {0.0})
    gaps = sorted({r[mode]["gap"] for r in rows} | {0.0}) if mode == "vector" else [0.0]
    best = None
    for tau_abs in tops + [max(tops) + 1e-6]:
        for tau_gap in gaps:
            passed = [r[mode]["top1"] >= tau_abs and r[mode]["gap"] >= tau_gap for r in rows]
            false_pass = sum(p for p, r in zip(passed, rows) if not r["expected"])
            false_block = sum(not p for p, r in zip(passed, rows) if r["expected"])
            if false_pass:
                continue
            key = (false_block, -tau_abs, -tau_gap)
            if best is None or key < best[0]:
                best = (key, {"tau_abs": tau_abs, "tau_gap": tau_gap, "false_block": false_block})
    return best[1]


def confusion(rows: list[dict], mode: str, rule: dict) -> dict:
    out = {"evidence_passed": 0, "evidence_blocked": 0, "no_evidence_passed": 0, "no_evidence_blocked": 0}
    for r in rows:
        passed = r[mode]["top1"] >= rule["tau_abs"] and r[mode]["gap"] >= rule["tau_gap"]
        key = ("evidence_" if r["expected"] else "no_evidence_") + ("passed" if passed else "blocked")
        out[key] += 1
    return out


def hit_at_3(rows: list[dict], mode: str) -> dict:
    scored = [r for r in rows if r["expected"]]
    hits = sum(bool(set(r["expected"]) & set(r[mode]["top3"])) for r in scored)
    by_type: dict[str, list[int]] = {}
    for r in scored:
        by_type.setdefault(r["type"], [0, 0])
        by_type[r["type"]][0] += bool(set(r["expected"]) & set(r[mode]["top3"]))
        by_type[r["type"]][1] += 1
    return {"hits": hits, "total": len(scored), "by_type": {k: f"{a}/{b}" for k, (a, b) in by_type.items()}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedder", choices=["e5", "fake"], required=True)
    parser.add_argument("--revision")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--index-dir", default="data/index")
    parser.add_argument("--out-dir", default="docs/evidence/B02b")
    args = parser.parse_args()
    scrub_environment()
    block_network()

    from app.rag.embeddings import make_embedder
    from app.rag.index import document_scores, open_active

    embedder = make_embedder(args.embedder, args.revision, args.device)
    index = open_active(Path(args.index_dir), embedding_model=embedder.model_id,
                        pinned_revision=embedder.revision, dimension=embedder.dimension,
                        normalization=embedder.normalization)
    items = json.loads(EVAL_FILE.read_text(encoding="utf-8"))["items"]
    rows = []
    try:
        for item in items:
            query = query_for(item["intake"])
            row = {"id": item["id"], "split": item["split"], "type": item["type"], "expected": item["expected"]}
            t0 = time.monotonic()
            lex_hits = index.search_lex(query, k=10)
            t1 = time.monotonic()
            qvec = embedder.encode_query(query)
            t2 = time.monotonic()
            vec_hits = index.search_vector(qvec, k=10)
            t3 = time.monotonic()
            for mode, hits, ms in (("lex", lex_hits, {"search_ms": (t1 - t0) * 1000}),
                                   ("vector", vec_hits, {"embed_ms": (t2 - t1) * 1000, "search_ms": (t3 - t2) * 1000})):
                docs = document_scores(hits)
                top1 = docs[0][1] if docs else 0.0
                top2 = docs[1][1] if len(docs) > 1 else 0.0
                row[mode] = {"top3": [d for d, _ in docs[:3]], "scores": [round(s, 5) for _, s in docs[:3]],
                             "top1": top1, "gap": top1 - top2, **{k: round(v, 2) for k, v in ms.items()}}
            rows.append(row)
    finally:
        index.close()

    compare = [r for r in rows if r["split"] == "compare"]
    confirm = [r for r in rows if r["split"] == "confirm"]
    report = {"embedder": args.embedder, "real_model": args.embedder == "e5", "model": embedder.model_id,
              "revision": embedder.revision, "index_version": index.manifest.index_version,
              "random_baseline": RANDOM_BASELINE, "modes": {}}
    for mode in ("lex", "vector"):
        rule = calibrate(compare, mode)
        report["modes"][mode] = {
            "rule": {**rule, "calibrated_on": "compare", "version": f"{mode}-rule-{index.manifest.index_version}"},
            "hit_at_3": {"compare": hit_at_3(compare, mode), "confirm": hit_at_3(confirm, mode)},
            "gate": {"compare": confusion(compare, mode, rule), "confirm_applied_once": confusion(confirm, mode, rule)},
            "median_ms": {k: sorted(r[mode].get(k, 0) for r in rows)[len(rows) // 2]
                          for k in ("embed_ms", "search_ms") if k in rows[0][mode]},
        }
    report["network_attempts"] = ATTEMPTS
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval_eval.json").write_text(json.dumps({"summary": report, "rows": rows}, ensure_ascii=False,
                                                        indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if not ATTEMPTS else 1


if __name__ == "__main__":
    sys.exit(main())
