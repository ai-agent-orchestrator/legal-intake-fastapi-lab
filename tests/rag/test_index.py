import hashlib
import json
import math
import random
from types import SimpleNamespace

import pytest

from app.rag.index import MemvidIndex, apply_rule, lex_terms, publish_index
from app.rag.schemas import Chunk, Evidence, RetrievalStatus, RetrievalUnavailable


def synthetic_rows(count=30, version="unit-v1"):
    rng = random.Random(12)
    vectors, chunks = [], []
    for i in range(count):
        text = f"합성 보증금 계약서 준비 자료 {i}"
        chunks.append(Chunk(text, {"chunkId": f"C{i:03d}", "documentId": f"D{i:03d}",
            "contentHash": hashlib.sha256(text.encode()).hexdigest(), "embeddingModel": "synthetic-unit",
            "pinnedRevision": "unit-revision", "indexVersion": version}))
        raw = [rng.gauss(0,1) for _ in range(1024)]
        norm = math.sqrt(sum(x*x for x in raw))
        vectors.append([x/norm for x in raw])
    return chunks, vectors


def test_native_thirty_chunks_reopen_and_every_self_top1_before_activation(tmp_path):
    chunks, vectors = synthetic_rows()
    manifest = publish_index(chunks, vectors, index_dir=tmp_path, index_version="unit-v1",
                             embedding_model="synthetic-unit", pinned_revision="unit-revision")
    assert manifest["activationCheck"] == {"expected":30,"totalHits":30,"selfTop1":30,"batchMaximum":8}
    index = MemvidIndex(tmp_path, embedding_model="synthetic-unit", pinned_revision="unit-revision")
    try:
        assert len(index.search(mode="vector", query_vector=vectors[0])) == 30
        assert index.search(mode="vector", query_vector=vectors[-1])[0].chunk_id == "C029"
        assert index.search(mode="lex", query="CIVIL 보증금 없는단어 [PHONE] OR")
    finally:
        index.close()
    pointer = json.loads((tmp_path/"active.json").read_text())
    assert pointer["indexVersion"] == "unit-v1" and pointer["manifestSha256"]
    with pytest.raises(RetrievalUnavailable):
        MemvidIndex(tmp_path, embedding_model="wrong", pinned_revision="unit-revision")
    with pytest.raises(FileExistsError):
        publish_index(chunks, vectors, index_dir=tmp_path, index_version="unit-v1",
                      embedding_model="synthetic-unit", pinned_revision="unit-revision")


@pytest.mark.parametrize("failure", ["count", "self"])
def test_failed_activation_preserves_previous_pointer_and_put_options(tmp_path, monkeypatch, failure):
    # Fake SDK injects failures; the separate test above uses the native SDK.
    chunks, vectors = synthetic_rows(30)
    old = b'{"previous":"unchanged"}'
    (tmp_path/"active.json").write_bytes(old)
    writes = []
    class Writer:
        def put_many(self, requests, **kwargs):
            assert kwargs["opts"] == {"enable_embedding":False}
            assert len(requests) <= 8
            writes.append(requests)
        def seal(self): pass
        def close(self): pass
    class Reader:
        def find(self, query, **kwargs):
            if kwargs["k"] == 30:
                return {"total_hits":29 if failure=="count" else 30,
                        "hits":[{"title":c.metadata["chunkId"]} for c in chunks]}
            return {"hits":[{"title":"wrong-self"}]}
        def close(self): pass
    def create(path, **kwargs):
        from pathlib import Path
        Path(path).write_bytes(b"fake-index-for-failure-injection")
        return Writer()
    monkeypatch.setattr("app.rag.index.load_memvid", lambda:SimpleNamespace(create=create, use=lambda *a,**k:Reader()))
    with pytest.raises(RetrievalUnavailable):
        publish_index(chunks,vectors,index_dir=tmp_path,index_version="unit-v1",
                      embedding_model="synthetic-unit",pinned_revision="unit-revision")
    assert (tmp_path/"active.json").read_bytes() == old
    assert [len(r) for r in writes] == [8,8,8,6]


def test_or_terms_remove_masks_labels_operators_and_query_syntax():
    assert lex_terms('CIVIL [PHONE] [EMAIL] OR AND NOT 보증금 없는단어 "계약서"') == ["보증금","없는단어","계약서"]


def test_thresholds_distinguish_no_results_low_relevance_and_good_evidence():
    evidence = [Evidence("D1","C1",0.9),Evidence("D2","C2",0.8)]
    assert apply_rule([],mode="vector",index_version="v",tau_abs=0).status == RetrievalStatus.EMPTY
    assert apply_rule(evidence,mode="vector",index_version="v",tau_abs=.8,tau_gap=.2).status == RetrievalStatus.BELOW_THRESHOLD
    assert apply_rule(evidence,mode="vector",index_version="v",tau_abs=.8,tau_gap=.05).status == RetrievalStatus.OK
    assert apply_rule(evidence,mode="lex",index_version="v",tau_abs=.8,tau_gap=2).status == RetrievalStatus.OK
