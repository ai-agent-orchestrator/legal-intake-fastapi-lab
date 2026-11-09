"""OFFLINE CANDIDATES ONLY. Not imported by the application or canonical policy.

Deliberately narrow label rules let synthetic evaluation expose both false
positives and missed free-form entities before any production rule is approved.
"""
import re

RULE_VERSION = "masking-scope-candidates-2026-11-09-v1"
RULE_BUNDLES = {"NAME": "name-label-v1", "ADDRESS": "address-label-v1", "CASE_NUMBER": "case-pattern-v1"}
RULES = (
    ("NAME", re.compile(r"(?:성명|이름)\s*[:：]\s*([가-힣]{2,4})"), 1),
    ("ADDRESS", re.compile(r"주소\s*[:：]\s*([^.!?\n]+)"), 1),
    ("CASE_NUMBER", re.compile(r"(?<!\d)20\d{2}(?:가단|가합|고단|고합|나|다|드단)\d{1,6}(?!\d)"), 0),
)


def candidate_spans(text: str) -> set[tuple[str, int, int]]:
    return {(name, match.start(group), match.end(group))
            for name, pattern, group in RULES for match in pattern.finditer(text)}
