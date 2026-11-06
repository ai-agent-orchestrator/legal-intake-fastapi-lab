import pytest

from app.rag.evaluation import calibrate, metrics
from app.rag.schemas import Evidence


def row(qid, correct, top, split="compare"):
    return {"questionId":qid,"expectedDocumentIds":correct,"split":split,
            "vector":{"top":top,"searchMs":1.0},"lex":{"top":top,"searchMs":2.0}}


def test_threshold_selection_rejects_negatives_then_preserves_positives():
    rows = [row("P",["A"],[Evidence("A","1",.9),Evidence("B","2",.6)]),
            row("N",[],[Evidence("B","2",.8),Evidence("A","1",.7)])]
    for mode in ("lex","vector"):
        chosen = calibrate(rows,mode)
        assert chosen["falseEvidenceCompare"] == 0 and chosen["falseNoEvidenceCompare"] == 0
        assert chosen["tau_abs"] == .9


def test_heldout_never_accepted_by_calibration():
    with pytest.raises(ValueError,match="compare"):
        calibrate([row("confirm",[],[],split="holdout")],"vector")


def test_hit_metrics_use_document_ids_and_positive_denominator():
    rows = [row("P",["A"],[Evidence("B","b",.9),Evidence("A","a",.8)]),row("N",[],[])]
    result = metrics(rows,"vector",{"tau_abs":.95,"tau_gap":0})
    assert result["Hit@1"]["fraction"] == "0/1"
    assert result["Hit@3"]["fraction"] == "1/1"
    assert result["confusionCounts"] == {"evidence_accepted":0,"evidence_rejected":1,
                                          "noEvidence_accepted":0,"noEvidence_rejected":1}


def test_timeout_kills_worker_tree_before_only_one_smaller_batch_retry(tmp_path, monkeypatch):
    import subprocess
    import scripts.evaluate_retrieval as runner
    commands, kills = [], []
    class Process:
        pid = 424242
        def __init__(self, command, **kwargs):
            commands.append(command)
            self.calls = 0
        def communicate(self, timeout=None):
            self.calls += 1
            if timeout is not None:
                assert timeout == 180
                raise subprocess.TimeoutExpired(commands[-1],timeout)
            return "", ""
        def kill(self):
            kills.append(["posix-worker"])
    monkeypatch.setattr(runner,"EVIDENCE",tmp_path)
    monkeypatch.setattr(runner.subprocess,"Popen",Process)
    monkeypatch.setattr(runner.subprocess,"run",lambda cmd,**kwargs:kills.append(cmd))
    with pytest.raises(RuntimeError,match="one reduced-batch retry"):
        runner.encode("documents",tmp_path)
    assert len(commands)==2 and len(kills)==2
    assert commands[0][commands[0].index("--batch")+1] == "2"
    assert commands[1][commands[1].index("--batch")+1] == "1"
    if runner.os.name == "nt":
        assert all(cmd == ["taskkill","/PID","424242","/T","/F"] for cmd in kills)
