import hashlib
import json
import socket
from collections import Counter
from dataclasses import asdict

import pytest

from app.core.config import Settings
from app.rag.corpus import (ROOT, chunk_guides, load_guides, load_tokenizer,
                            make_query, model_config, query_input)
from app.schemas.intake import IntakeCreateRequest


@pytest.fixture(scope="module")
def tokenizer():
    return load_tokenizer()


def test_offline_fixture_really_blocks_sockets():
    with pytest.raises(AssertionError, match="Network forbidden"):
        socket.create_connection(("example.invalid", 443))


def test_document_lengths_cases_and_synthetic_notice(tokenizer):
    guides = load_guides()
    assert len(guides) == 10 and len({g["documentId"] for g in guides}) == 10
    assert set(Counter(g["caseType"] for g in guides)) == {"CIVIL", "CRIMINAL", "FAMILY", "OTHER"}
    assert min(Counter(g["caseType"] for g in guides).values()) >= 2
    for guide in guides:
        assert guide["text"].splitlines()[0] == "합성 학습 자료, 법률 자문 아님"
        assert 600 <= len(tokenizer.encode(guide["text"])) <= 1200


def test_eval_dtos_splits_tags_and_final_query_lengths(tokenizer):
    records = json.loads((ROOT / "fixtures/rag/evaluation.json").read_text(encoding="utf-8"))
    assert len(records) == 30
    for split, count, negative in [("compare", 20, 6), ("holdout", 10, 4)]:
        rows = [r for r in records if r["split"] == split]
        assert len(rows) == count
        assert sum(not r["expectedDocumentIds"] for r in rows) >= negative
    assert {t for r in records for t in r["tags"]} == {"의역", "법률 용어", "무근거", "합성 PII"}
    for record in records:
        dto = record["intake"]
        IntakeCreateRequest.model_validate(dto)
        query = make_query(dto)
        assert dto["clientName"] not in query
        assert "@" not in query and "010-0000-0000" not in query
        assert len(tokenizer.encode(query_input(query))) <= model_config()["maxInputTokens"]


def test_chunks_preserve_titles_metadata_and_content_hash(tokenizer):
    chunks = chunk_guides(load_guides(), tokenizer)
    assert len(chunks) > 10
    assert len({c.metadata["chunkId"] for c in chunks}) == len(chunks)
    for chunk in chunks:
        meta = chunk.metadata
        assert len(meta) == 13 and chunk.text.startswith(meta["title"]+"\n\n")
        assert meta["contentHash"] == hashlib.sha256(chunk.text.encode()).hexdigest()
        assert meta["tokenCount"] == len(tokenizer.encode(chunk.text)) <= 300
        assert "Instruct:" not in chunk.text


def test_reingestion_is_idempotent_and_changed_sources_have_new_ids(tokenizer):
    guides = load_guides()
    first = chunk_guides(guides, tokenizer)
    again = chunk_guides(guides + guides, tokenizer)
    assert [asdict(c) for c in first] == [asdict(c) for c in again]
    changed = chunk_guides([{**g, "sourceVersion": "synthetic-2"} for g in guides], tokenizer)
    assert not ({c.metadata["chunkId"] for c in first} & {c.metadata["chunkId"] for c in changed})


def test_rag_remains_off_and_retrieval_has_no_api_connection():
    from app.main import create_app
    config = Settings(_env_file=None)
    assert config.rag_enabled is False
    paths = create_app(config).openapi()["paths"]
    assert set(paths) == {"/api/intakes", "/api/intakes/{intake_id}", "/api/intakes/{intake_id}/guidance"}
