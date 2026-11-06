"""Golden-set metrics and compare-only calibration, no model/store imports."""
import math

from app.rag.index import apply_rule
from app.rag.schemas import RetrievalStatus


def relevant(top, mode, thresholds):
    return apply_rule(top, mode=mode,index_version="e5-v1",**thresholds).status == RetrievalStatus.OK


def calibrate(rows, mode):
    # Rows contain compare20 only; heldout is never accepted by this interface.
    if any(r["split"] != "compare" for r in rows):
        raise ValueError("Threshold calibration accepts compare rows only")
    scores = [r[mode]["top"][0].score for r in rows if r[mode]["top"]]
    gaps = [r[mode]["top"][0].score-(r[mode]["top"][1].score if len(r[mode]["top"])>1 else 0)
            for r in rows if r[mode]["top"]]
    absolutes = sorted({0.0,*scores,*(math.nextafter(x,math.inf) for x in scores)})
    gap_candidates = sorted({0.0,*gaps,*(math.nextafter(x,math.inf) for x in gaps)}) if mode=="vector" else [0.0]
    candidates = []
    for absolute in absolutes:
        for gap in gap_candidates:
            thresholds = {"tau_abs":absolute,"tau_gap":gap}
            decisions = [relevant(r[mode]["top"],mode,thresholds) for r in rows]
            false_evidence = sum(ok and not r["expectedDocumentIds"] for r,ok in zip(rows,decisions))
            if false_evidence:
                continue
            false_no = sum(not ok and bool(r["expectedDocumentIds"]) for r,ok in zip(rows,decisions))
            candidates.append((false_no,-absolute,-gap,thresholds))
    if not candidates:
        raise ValueError("No thresholds satisfy compare negative constraint")
    winner = min(candidates,key=lambda c:c[:3])
    return {**winner[3],"falseEvidenceCompare":0,"falseNoEvidenceCompare":winner[0]}


def metrics(rows, mode, thresholds):
    positive = [r for r in rows if r["expectedDocumentIds"]]
    output = {"evidenceQuestions":len(positive),"totalQuestions":len(rows)}
    for k in (1,3):
        hits = sum(bool(set(e.document_id for e in r[mode]["top"][:k]) & set(r["expectedDocumentIds"])) for r in positive)
        output[f"Hit@{k}"] = {"n":hits,"total":len(positive),"fraction":f"{hits}/{len(positive)}" if positive else "N/A (no evidence questions)"}
    confusion = {"evidence_accepted":0,"evidence_rejected":0,"noEvidence_accepted":0,"noEvidence_rejected":0}
    for row in rows:
        actual = "evidence" if row["expectedDocumentIds"] else "noEvidence"
        decision = "accepted" if relevant(row[mode]["top"],mode,thresholds) else "rejected"
        confusion[actual+"_"+decision] += 1
    output["confusionCounts"] = confusion
    latencies = sorted(r[mode]["searchMs"] for r in rows)
    output["searchLatencyMs"] = {"mean":sum(latencies)/len(latencies) if latencies else None,
                                "p95":latencies[max(0,math.ceil(.95*len(latencies))-1)] if latencies else None}
    return output
