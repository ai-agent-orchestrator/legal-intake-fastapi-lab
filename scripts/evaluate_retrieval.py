"""One-shot confirm evaluation; thresholds frozen before confirm embedding/search."""
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.rag.corpus import chunk_guides, load_guides, load_tokenizer, make_query, model_config
from app.rag.evaluation import calibrate, metrics
from app.rag.index import MemvidIndex, apply_rule, publish_index, sha256_file
from app.rag.offline import offline

EVIDENCE = ROOT/"docs/evidence/B02b"


def write_json(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def encode(phase, work):
    import numpy as np
    output = work/(phase+".npy")
    attempts = []
    for batch in (2,1):
        command = [sys.executable,str(ROOT/"scripts/encode_e5.py"),"--phase",phase,"--batch",str(batch),"--output",str(output)]
        started = time.perf_counter()
        process = subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   text=True,encoding="utf-8")
        try:
            stdout, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            # Windows venv launcher may spawn a base-python child: kill the whole
            # worker tree, not only its launcher, before releasing CPU/retrying.
            if os.name == "nt":
                subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                               capture_output=True,check=True)
            else:
                process.kill()
            process.communicate()
            attempts.append({"batch":batch,"timeout":True,"wallSeconds":time.perf_counter()-started})
            write_json(EVIDENCE/("encode_attempts_"+phase+".json"),attempts)
            if batch == 1:
                raise RuntimeError("E5 wall timeout after one reduced-batch retry")
            continue
        attempts.append({"batch":batch,"timeout":False,"wallSeconds":time.perf_counter()-started,"exitCode":process.returncode})
        (EVIDENCE/("encode_"+phase+".txt")).write_text(stdout+stderr,encoding="utf-8")
        write_json(EVIDENCE/("encode_attempts_"+phase+".json"),attempts)
        if process.returncode:
            raise RuntimeError("Offline E5 worker failed; see encode evidence")
        report = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        write_json(EVIDENCE/("embedding_"+phase+".json"),report)
        return np.load(output,allow_pickle=False), report


def retrieve(rows, vectors, embedding_report, index):
    output = []
    if len(rows) != len(vectors) or [r["questionId"] for r in rows] != embedding_report["ids"]:
        raise RuntimeError("Query/vector order mismatch")
    for number, (record, vector) in enumerate(zip(rows,vectors)):
        item = {k:record[k] for k in ("questionId","split","tags","expectedDocumentIds")}
        item["hasEvidence"] = bool(record["expectedDocumentIds"])
        item["queryEmbeddingMs"] = embedding_report["individualQueryEmbeddingMs"][number]
        for mode in ("lex","vector"):
            started = time.perf_counter()
            top = index.search(mode=mode,query=make_query(record["intake"]),query_vector=vector)
            item[mode] = {"top":top,"searchMs":1000*(time.perf_counter()-started)}
        output.append(item)
    return output


def main():
    if (EVIDENCE/"confirm_once.json").exists() or (EVIDENCE/"retrieval_eval.json").exists():
        raise RuntimeError("Confirm is one-shot; refusing another evaluation")
    gate = json.loads((ROOT/"docs/evidence/B02a/memvid_workaround_windows.json").read_text())
    if not gate["workaroundGatePassed"]:
        raise RuntimeError("B02a workaround gate did not pass")
    work = ROOT/"data/evaluation-output"/uuid4().hex
    work.mkdir(parents=True)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    source = ROOT/"fixtures/rag/evaluation.json"
    records = json.loads(source.read_text(encoding="utf-8"))
    config = model_config()
    with offline():
        document_vectors, document_report = encode("documents",work)
        tokenizer = load_tokenizer()
        chunks = chunk_guides(load_guides(),tokenizer,"e5-v1")
        if document_report["ids"] != [c.metadata["chunkId"] for c in chunks]:
            raise RuntimeError("Document/vector order mismatch")
        manifest = publish_index(chunks,document_vectors,index_dir=ROOT/"data/index",index_version="e5-v1",
            embedding_model=config["embeddingModel"],pinned_revision=config["pinnedRevision"])
        # Evidence omits text/vectors but preserves activation/provenance identities.
        write_json(EVIDENCE/"index_activation.json",{k:v for k,v in manifest.items() if k!="chunks"})
        comparison_vectors, comparison_report = encode("compare",work)
        index = MemvidIndex(ROOT/"data/index",embedding_model=config["embeddingModel"],pinned_revision=config["pinnedRevision"])
        try:
            comparison = retrieve([r for r in records if r["split"]=="compare"],comparison_vectors,comparison_report,index)
            calibrated = {mode:calibrate(comparison,mode) for mode in ("lex","vector")}
            thresholds = {mode:{k:v for k,v in values.items() if k in {"tau_abs","tau_gap"}} for mode,values in calibrated.items()}
            frozen = {"calibratedOn":"compare20 ONLY","thresholds":thresholds,"trainingCounts":calibrated,
                      "evaluationSha256":sha256_file(source),"indexVersion":"e5-v1","model":config}
            write_json(EVIDENCE/"frozen_thresholds.json",frozen)
            # Exclusive marker BEFORE confirm encoding/search; never delete to retune.
            with (EVIDENCE/"confirm_once.json").open("x",encoding="utf-8") as marker:
                json.dump({"thresholdsSha256":sha256_file(EVIDENCE/"frozen_thresholds.json"),
                           "evaluationSha256":sha256_file(source),"phase":"reserved before first confirm search"},marker,indent=2)
            confirm_vectors, confirm_report = encode("confirm",work)
            confirm = retrieve([r for r in records if r["split"]=="holdout"],confirm_vectors,confirm_report,index)
        finally:
            index.close()
    rows = comparison+confirm
    summary = {}
    for split in ("compare","holdout"):
        subset = [r for r in rows if r["split"]==split]
        summary[split] = {mode:metrics(subset,mode,thresholds[mode]) for mode in ("lex","vector")}
    summary["byTag"] = {}
    for tag in ("의역","법률 용어","합성 PII","무근거"):
        summary["byTag"][tag] = {split:{mode:metrics([r for r in rows if r["split"]==split and tag in r["tags"]],mode,thresholds[mode])
            for mode in ("lex","vector")} for split in ("compare","holdout")}
    serialized = []
    for row in rows:
        value = {k:v for k,v in row.items() if k not in {"lex","vector"}}
        for mode in ("lex","vector"):
            state = apply_rule(row[mode]["top"],mode=mode,index_version="e5-v1",**thresholds[mode])
            value[mode] = {"top3":[asdict(e) for e in row[mode]["top"][:3]],
                           "allDocumentScores":[asdict(e) for e in row[mode]["top"]],
                           "status":state.status.value,"searchMs":row[mode]["searchMs"]}
        serialized.append(value)
    report = {"actualE5":True,"actualMemvid":True,"syntheticCorpusOnly":True,
              "model":config,"indexVersion":"e5-v1","thresholds":thresholds,
              "scoreMeaning":"native memvid semantic score, NOT raw cosine or legal correctness probability",
              "evaluationSha256":sha256_file(source),"confirmAppliedOnce":True,
              "randomHit3Baseline":{"n":3,"total":10,"assumptions":"10 docs, one relevant, uniform sampling without replacement"},
              "rows":serialized,"metrics":summary}
    write_json(EVIDENCE/"retrieval_eval.json",report)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
