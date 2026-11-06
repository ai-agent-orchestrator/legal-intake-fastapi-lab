"""B01 synthetic corpus contract: structure only, no model or network required."""
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from app.schemas.intake import IntakeCreateRequest

ROOT = Path(__file__).resolve().parents[1] / "corpus" / "synthetic"
MANIFEST = json.loads((ROOT / "guides.json").read_text(encoding="utf-8"))
EVAL = json.loads((ROOT / "eval" / "intakes.json").read_text(encoding="utf-8"))
DOCS = {d["documentId"]: d for d in MANIFEST["documents"]}
ITEMS = EVAL["items"]
DISCLAIMER = "합성 학습 자료이며 법률 자문이 아닙니다"
PII = re.compile(r"(?<!\d)0?1[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")


def text(doc_id):
    return (ROOT / DOCS[doc_id]["file"]).read_text(encoding="utf-8")


def test_ten_guides_with_case_type_balance_and_similar_pairs():
    assert len(DOCS) == 10 and len(MANIFEST["documents"]) == 10
    counts = Counter(d["caseType"] for d in DOCS.values())
    assert set(counts) == {"CIVIL", "CRIMINAL", "FAMILY", "OTHER"} and min(counts.values()) >= 2
    assert len(MANIFEST["similarPairs"]) >= 2
    assert all(a in DOCS and b in DOCS for a, b in MANIFEST["similarPairs"])


@pytest.mark.parametrize("doc_id", sorted(DOCS))
def test_guide_file_shape(doc_id):
    body = text(doc_id)
    first_line = body.splitlines()[0]
    assert DISCLAIMER in first_line
    assert f"# {DOCS[doc_id]['title']}" in body
    # Provenance lives in guides.json, never inside the indexed text.
    assert doc_id not in body and "documentId" not in body
    # Character bounds stand in for 600~1,200 E5 tokens until B01 measures real token counts.
    assert 900 <= len(body) <= 2600
    assert not PII.search(body)


def test_eval_split_and_type_counts():
    assert len(ITEMS) == 30 and len({i["id"] for i in ITEMS}) == 30
    compare = [i for i in ITEMS if i["split"] == "compare"]
    confirm = [i for i in ITEMS if i["split"] == "confirm"]
    assert len(compare) == 20 and len(confirm) == 10
    assert sum(i["type"] == "no_evidence" for i in compare) >= 6
    assert sum(i["type"] == "no_evidence" for i in confirm) >= 4
    assert {i["type"] for i in ITEMS} == set(EVAL["types"])


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_eval_item_contract(item):
    # Every item is a valid intake DTO under the existing API contract.
    IntakeCreateRequest.model_validate(item["intake"])
    assert all(e in DOCS for e in item["expected"])
    assert (item["type"] == "no_evidence") == (not item["expected"])
    query_fields = item["intake"]["coreStatement"] + (item["intake"]["desiredNextStep"] or "")
    if item["type"] == "paraphrase":
        for doc_id in item["expected"]:
            assert not any(word in query_fields for word in DOCS[doc_id]["titleKeywords"]), item["id"]
    if item["type"] == "pii":
        assert PII.search(query_fields)
    else:
        assert not PII.search(query_fields)


def test_every_guide_is_expected_somewhere_in_compare_split():
    covered = {e for i in ITEMS if i["split"] == "compare" for e in i["expected"]}
    assert covered == set(DOCS)
