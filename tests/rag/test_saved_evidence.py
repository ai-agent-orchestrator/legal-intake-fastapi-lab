import hashlib
import json

from app.rag.corpus import ROOT, model_config
from scripts.report_retrieval import recompute


def test_saved_metrics_threshold_freeze_and_confirm_identity_recompute_without_search():
    folder = ROOT/"docs/evidence/B02b"
    report = json.loads((folder/"retrieval_eval.json").read_text(encoding="utf-8"))
    frozen = json.loads((folder/"frozen_thresholds.json").read_text(encoding="utf-8"))
    marker = json.loads((folder/"confirm_once.json").read_text(encoding="utf-8"))
    source_hash = hashlib.sha256((ROOT/"fixtures/rag/evaluation.json").read_bytes()).hexdigest()
    assert report["evaluationSha256"] == frozen["evaluationSha256"] == marker["evaluationSha256"] == source_hash
    assert marker["thresholdsSha256"] == hashlib.sha256((folder/"frozen_thresholds.json").read_bytes()).hexdigest()
    assert report["thresholds"] == frozen["thresholds"]
    assert report["model"] == model_config() and report["actualE5"] and report["actualMemvid"]
    assert len(report["rows"]) == 30 and len({r["questionId"] for r in report["rows"]}) == 30
    assert sum(r["split"]=="holdout" for r in report["rows"]) == 10
    assert recompute(report) == report["metrics"]
