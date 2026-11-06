"""Legacy initial B02a probe (3 vectors); superseded by probe_memvid_workaround.py.

Preserved to reproduce the initial stop, not the approved activation gate.
"""
import gc
import json
import os
import socket
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
os.environ["MEMVID_TELEMETRY"] = "0"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def block_socket(*args, **kwargs):
    raise AssertionError("Network forbidden in memvid capability probe")


def main():
    socket.socket.connect = block_socket
    socket.socket.connect_ex = block_socket
    socket.create_connection = block_socket
    socket.getaddrinfo = block_socket
    from memvid_sdk import create, use

    folder = ROOT / "data/probes" / uuid4().hex
    folder.mkdir(parents=True)
    output = ROOT / "docs/evidence/B02a/memvid_capabilities.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"sdk": "memvid-sdk==2.0.160", "actualSdk": True,
              "vectorSource": "deterministic artificial 1024D unit basis; NOT E5",
              "network": "Python sockets blocked; MEMVID_TELEMETRY=0; no keys supplied",
              "checks": {}}

    def record(name, passed, detail):
        report["checks"][name] = {"pass": bool(passed), "evidence": detail}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(name, "PASS" if passed else "FAIL", json.dumps(detail, ensure_ascii=False), flush=True)

    vectors = [[float(sign if column == axis else 0) for column in range(1024)]
               for axis, sign in [(0, 1), (1, 1), (0, -1)]]
    docs = [{"title": "synthetic "+name, "label": "synthetic", "text": text,
             "metadata": {"documentId": name, "chunkId": name+":0", "testMarker": "synthetic-only"}}
            for name, text in [("A", "synthetic alpha loan preparation"),
                               ("B", "synthetic beta rent preparation"),
                               ("C", "synthetic gamma inheritance preparation")]]
    path = folder / "capability.mv2"
    handle = None
    try:
        handle = create(str(path), enable_vec=True, enable_lex=True)
        ids = handle.put_many(docs, embeddings=vectors,
            embedding_identity={"provider": "external", "model": "synthetic-basis-1024"})
        handle.seal()
        record("external_document_vectors", len(ids) == 3, {"frameIds": ids})
        sem = handle.find("synthetic", mode="sem", query_embedding=vectors[0], k=3)
        record("query_vector_search", bool(sem.get("hits")), sem)
        lex = handle.find("loan", mode="lex", k=3)
        record("lex_search", bool(lex.get("hits")), lex)
        hits = sem.get("hits", [])
        record("metadata_return", all(h.get("metadata", {}).get("documentId") for h in hits) and len(hits)==3,
               [{"keys": sorted(h), "metadata": h.get("metadata")} for h in hits])
        try:
            wrong = handle.find("synthetic", mode="sem", query_embedding=[1.0]*1023, k=3)
        except Exception as exc:
            record("query_dimension_mismatch_rejected", True, {"type": type(exc).__name__, "message": str(exc)})
        else:
            record("query_dimension_mismatch_rejected", False, {"returnedInsteadOfRejecting": wrong})
        try:
            handle.put_many([docs[0]], embeddings=[[0.0]*1023])
        except Exception as exc:
            record("stored_dimension_mismatch_rejected", True, {"type": type(exc).__name__, "message": str(exc)})
        else:
            record("stored_dimension_mismatch_rejected", False, "1023D insert into 1024D index unexpectedly accepted")
        # Scores are inspected, not re-labelled as cosine without evidence.
        record("score_direction", len(hits)==3 and hits[0].get("title")=="synthetic A"
               and hits[-1].get("title")=="synthetic C"
               and hits[0].get("score", 0)>hits[-1].get("score", 0),
               [{"title": h.get("title"), "score": h.get("score")} for h in hits])
        handle.close()
        handle = use("basic", str(path), read_only=True, enable_vec=True, enable_lex=True)
        reopened = handle.find("synthetic", mode="sem", query_embedding=vectors[0], k=3)
        projection = lambda result: [(h.get("frame_id"), h.get("title"), h.get("score")) for h in result.get("hits", [])]
        record("reopen_same_results", projection(sem)==projection(reopened), reopened)
        handle.close()
        handle = None
        for operation in ("replace", "delete"):
            target = folder / (operation+".mv2")
            other = folder / (operation+"-replacement.mv2")
            target.write_bytes(path.read_bytes())
            if operation == "replace":
                other.write_bytes(path.read_bytes())
            opened = use("basic", str(target), read_only=True)
            try:
                try:
                    os.replace(other, target) if operation == "replace" else target.unlink()
                    observation = "allowed while open"
                except OSError as exc:
                    observation = {"behavior": "rejected while open", "winerror": exc.winerror, "type": type(exc).__name__}
                record("windows_open_"+operation+"_observed", True, observation)
            finally:
                opened.close()
            # Windows cleanup occurs only after the handle is closed, in probe folder.
            for file in (target, other):
                if file.exists():
                    file.unlink()
        try:
            use("basic", str(folder / "missing.mv2"), read_only=True)
        except Exception as exc:
            record("failure_no_silent_fallback", True, {"type": type(exc).__name__, "message": str(exc)})
        else:
            record("failure_no_silent_fallback", False, "missing index unexpectedly opened")
    except Exception as exc:
        record("probe_execution", False, {"type": type(exc).__name__, "message": str(exc)})
    finally:
        if handle is not None:
            handle.close()
        gc.collect()
        required = ["external_document_vectors", "query_vector_search", "lex_search", "metadata_return",
                    "query_dimension_mismatch_rejected", "stored_dimension_mismatch_rejected", "score_direction",
                    "reopen_same_results", "windows_open_replace_observed", "windows_open_delete_observed",
                    "failure_no_silent_fallback"]
        for name in required:
            if name not in report["checks"]:
                record(name, False, "Not reached because a previous prerequisite failed")
        report["allMandatoryPassed"] = all(report["checks"][name]["pass"] for name in required)
        report["nextAction"] = "continue B02b" if report["allMandatoryPassed"] else "STOP; no alternative store or E5 weights"
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return 0 if report["allMandatoryPassed"] else 2


if __name__ == "__main__":
    sys.exit(main())
