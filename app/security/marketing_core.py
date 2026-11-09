"""Standalone project wording policy, sourced only from LEGAL_MARKETING_BOARD.md.

This is not an advertising-law compliance classifier. Rules beyond the three
documented guarantees require a separately reviewed rule bundle.
"""
from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata

RULE_VERSION = "marketing-guarantees-2026-11-09-v1"
MAX_OUTPUT_CHARS = 8000


class Decision(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"


class MarketingError(ValueError):
    pass


@dataclass(frozen=True)
class MarketingDecision:
    decision: Decision
    safe_draft: str
    review_required: bool = False
    reason_code: str = "SAFE"
    matched_rules: tuple[str, ...] = ()
    rule_version: str = RULE_VERSION


_RULES = (
    ("WIN_100_PERCENT", re.compile(r"100%승소보장")),
    ("UNCONDITIONAL_WIN", re.compile(r"무조건승소")),
    ("COMPENSATION_PROMISE", re.compile(r"반드시보상받습니다")),
)
# Exempt only direct denials or explicit rejection of a quoted expression.
# Another denial elsewhere in the output never exempts an affirmative claim.
_DENIAL = re.compile(
    r"^[\s'\"‘’“”「」]*(?:(?:을|를|은|는)?보장)?(?:을|를|은|는)?"
    r"(?:하지않|하지못|하지는않|할수없|하지말|하지마|아닙|아니며)|"
    r"^[\s'\"‘’“”「」]*(?:같은|라는|이라는|와같은)?표현(?:을|은|는)?"
    r"(?:사용하지않|쓰지않|금지|피해|지양)"
)


def _view(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text)
                   if not c.isspace() and unicodedata.category(c) != "Cf")


def check_marketing_response(text: str) -> MarketingDecision:
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_OUTPUT_CHARS:
        raise MarketingError("MARKETING_INVALID_OUTPUT")
    safe_parts, matched = [], set()
    # Remove the complete sentence containing an affirmative claim. Never return
    # a partial promise or attach a disclaimer to an otherwise unchanged claim.
    for unit in re.findall(r"[^.!?。！？\n]+[.!?。！？]?|[\n.!?。！？]", text):
        view = _view(unit)
        risky = False
        for name, pattern in _RULES:
            for match in pattern.finditer(view):
                if not _DENIAL.search(view[match.end():]):
                    risky = True
                    matched.add(name)
        if not risky:
            safe_parts.append(unit)
    if not matched:
        return MarketingDecision(Decision.ALLOW, text)
    safe = "".join(safe_parts).strip()
    if not safe:
        safe = "보장 표현을 제외한 안내 문구는 담당자의 검토가 필요합니다."
    return MarketingDecision(Decision.REVIEW, safe, True, "MARKETING_REVIEW_REQUIRED", tuple(sorted(matched)))
