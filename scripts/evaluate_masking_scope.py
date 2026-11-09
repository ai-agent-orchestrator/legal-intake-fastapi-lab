"""Evaluate synthetic target entity spans. Does not enable application rules."""
from difflib import SequenceMatcher
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def evaluate():
    fixture = json.loads((ROOT / "fixtures/masking_scope_v1.json").read_text(encoding="utf-8"))
    candidates = runpy.run_path(str(ROOT / "experiments/masking_scope_v1.py"))
    canonical = runpy.run_path(str(ROOT / "app/security/policy_core.py"))
    reports = {}
    for method in ("canonical", "candidate"):
        by_type = {kind: {"tp": 0, "fp": 0, "fn": 0, "entities": 0, "cases": 0}
                   for kind in candidates["RULE_BUNDLES"]}
        details = []
        for row in fixture["cases"]:
            text, kind = row["text"], row["category"]
            gold = set()
            for value in row["entities"]:
                assert text.count(value) == 1, row["id"]
                start = text.index(value)
                gold.add((kind, start, start + len(value)))
            if method == "candidate":
                found = candidates["candidate_spans"](text)
            else:
                decision = canonical["mask_personal_data"](text)
                safe = decision.safe_text if decision.safe_text is not None else text
                # A canonical replacement overlapping a labelled entity counts as
                # detected only if it removed the entire expected entity span.
                changes = [(i, j) for op, i, j, _, _ in SequenceMatcher(None, text, safe).get_opcodes() if op != "equal"]
                found = {(kind, start, end) for start, end in changes}
            tp, fp, fn = len(found & gold), len(found - gold), len(gold - found)
            metrics = by_type[kind]
            for key, count in (("tp", tp), ("fp", fp), ("fn", fn), ("entities", len(gold)), ("cases", 1)):
                metrics[key] += count
            details.append({"case_id": row["id"], "tp": tp, "fp": fp, "fn": fn})
        reports[method] = {"by_type": by_type, "case_results": details}
    return {"fixture_version": fixture["version"], "label_note": fixture["label_note"],
            "candidate_version": candidates["RULE_VERSION"], "bundles": candidates["RULE_BUNDLES"],
            "runtime_enabled": False, "reports": reports}


if __name__ == "__main__":
    output = ROOT / "docs/evidence/MARKETING_2026-11-09/masking_scope.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluate(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
