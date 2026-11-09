"""Canonical, local rule actions. No network calls or retained request bodies.

These bounded patterns are not complete semantic abuse detection or de-identification.
D3/P0: this file imports ONLY the standard library. Package extraction is O4,
after legal-intake actions are complete; the folder structure stays unchanged.
"""
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    TRANSFORM = "TRANSFORM"


@dataclass(frozen=True)
class TextDecision:
    decision: Decision = Decision.ALLOW
    reason_code: str = "SAFE"
    detail_code: str | None = None
    safe_text: str | None = None
    matched_rules: tuple[str, ...] = ()


class PolicyError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

MASKING_VERSION = "legal-pii-2026-11-09-v1"
MAX_POLICY_CHARS = 20000
PROFILES = frozenset({"intake", "guidance", "marketing", "research", "retrieved"})
REASON_CODES = {
    "JAILBREAK":"BLOCKED_JAILBREAK", "PROMPT_INJECTION":"BLOCKED_PROMPT_INJECTION",
    "SECRET_REQUEST":"BLOCKED_SECRET_REQUEST", "PRIVACY_REQUEST":"BLOCKED_PRIVACY_RISK",
    "AUTH_BYPASS":"BLOCKED_AUTH_BYPASS", "LEGAL_ABUSE":"BLOCKED_LEGAL_HARM",
}


def _validate(text):
    if not isinstance(text, str) or len(text)>MAX_POLICY_CHARS:
        raise PolicyError("GUARDRAIL_INVALID_INPUT")


def _normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text)
                   if unicodedata.category(c) != "Cf")


# Rule IDs, never matching text, are returned for audit.
_INPUT_RULES = tuple((reason, re.compile(pattern, re.I)) for reason, pattern in (
    ("JAILBREAK", r"(?:ignore|disregard).{0,40}(?:previous|system|safety).{0,30}(?:instructions?|rules?)|"
     r"(?:규칙|이전지시|안전지침|시스템지시).{0,12}(?:무시|우회)|제한없는ai|\bdoanythingnow\b|\bjailbreak\b"),
    ("PROMPT_INJECTION", r"(?:시스템프롬프트|개발자메시지|숨은지시|내부정책).{0,16}(?:보여|출력|공개|알려)|"
     r"(?:show|reveal|print|dump).{0,24}(?:systemprompt|developermessage|hiddeninstructions?)|"
     r"<\|(?:im_start|system|endoftext)\|>|\[system\]"),
    ("SECRET_REQUEST", r"(?:apikey|api키|accesstoken|refreshtoken|password|비밀번호|환경변수|시크릿|secret|credential|\.env)"
     r".{0,16}(?:보여|알려|출력|공개|훔|추출)|(?:show|reveal|dump|steal|print).{0,24}"
     r"(?:apikey|accesstoken|password|secret|credential|\.env)|\bsk-[a-z0-9_-]{16,}"),
    ("PRIVACY_REQUEST", r"(?:상대방|타인|다른사람).{0,16}(?:주민번호|주민등록번호|주소|전화번호|계정정보)"
     r".{0,16}(?:알아|알려|보여|찾아|조회|추출)|(?:개인정보).{0,8}(?:알아내|훔|추출)"),
    ("AUTH_BYPASS", r"(?:전자서명|본인인증|인증|계정).{0,4}우회"),
    ("LEGAL_ABUSE", r"증거(?:를)?(?:조작해|조작하는법|조작방법|위조해|없애|삭제해|은폐해)|"
     r"(?:허위자료|허위문서|거짓진술|가짜문서)(?:를)?(?:만들어|만드는법|작성해)|"
     r"(?:forge|fabricate|destroy).{0,16}(?:evidence|testimony|documents?)"),
))

_MASK_RULES = (
    ("ID_NUMBER", re.compile(r"(?<!\d)\d{6}[-\s]?[1-8]\d{6}(?!\d)")),
    ("EMAIL", re.compile(r"(?<![a-z0-9.+-])[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
                         r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", re.I)),
    ("PHONE", re.compile(r"(?<!\d)(?:\+82[- .]?(?:0?10|0?2|0?[3-6][1-5]|0?70)|"
                         r"0(?:10|11|16|17|18|19|2|[3-6][1-5]|70))[- .]?\d{3,4}[- .]?\d{4}(?!\d)")),
)


def check_input_policy(text: str, *, profile: str = "guidance") -> TextDecision:
    # Normalize only the detection view; harmless input is preserved by this action.
    _validate(text)
    if profile not in PROFILES:
        raise PolicyError("GUARDRAIL_PROFILE_NOT_CONFIGURED")
    normalized = _normalize(text)
    if re.search(r"(?<![a-z0-9])sk-[a-z0-9_-]{16,}", normalized, re.I):
        return TextDecision(Decision.BLOCK, "BLOCKED_SECRET_REQUEST", matched_rules=("SECRET_REQUEST",))
    if re.search(r"(?<![a-z])(?:dan|jailbreak|roleplay)(?![a-z])", normalized, re.I):
        return TextDecision(Decision.BLOCK, "BLOCKED_JAILBREAK", matched_rules=("JAILBREAK",))
    text = re.sub(r"\s+", "", normalized).casefold()
    for reason, pattern in _INPUT_RULES:
        if pattern.search(text):
            return TextDecision(Decision.BLOCK, REASON_CODES[reason], matched_rules=(reason,))
    if profile in {"intake", "guidance"}:
        legal = ("법률", "상담", "사건", "분쟁", "피해", "소송", "증거", "자료", "계약", "반환", "이혼", "상속", "입금", "절차")
        unrelated = ("오늘날씨", "날씨알려", "주식추천", "코인추천", "맛집추천", "여행코스", "요리법", "레시피", "게임공략", "코딩해줘")
        if not any(word in text for word in legal) and any(word in text for word in unrelated):
            return TextDecision(Decision.BLOCK, "OUT_OF_SCOPE_TOPIC", matched_rules=("TOPIC",))
    return TextDecision(Decision.ALLOW, "ALLOWED")


def mask_personal_data(text: str) -> TextDecision:
    _validate(text)
    # Use a normalized detection view, but replace spans in the ORIGINAL text.
    # E.g. legal list marker ① and non-PII whitespace must not be rewritten.
    view, positions = [], []
    for offset, char in enumerate(text):
        for normalized in unicodedata.normalize("NFKC", char):
            if unicodedata.category(normalized) != "Cf":
                view.append(normalized)
                positions.append(offset)
    normalized = "".join(view)
    spans = []
    for name, pattern in _MASK_RULES:
        for match in pattern.finditer(normalized):
            start, end = positions[match.start()], positions[match.end()-1]+1
            if not any(start < b and end > a for a,b,_ in spans):
                spans.append((start,end,name))
    safe = text
    for start,end,name in sorted(spans,reverse=True):
        safe = safe[:start]+f"[{name}]"+safe[end:]
    if spans:
        return TextDecision(Decision.TRANSFORM, "PERSONAL_DATA_MASKED", detail_code=MASKING_VERSION,
                              safe_text=safe, matched_rules=tuple(sorted({name for _,_,name in spans})))
    return TextDecision()


def check_output_policy(text: str, *, max_chars: int = 8000, profile: str = "guidance") -> TextDecision:
    if not isinstance(text, str):
        raise PolicyError("GUARDRAIL_INVALID_INPUT")
    if not text.strip():
        return TextDecision(Decision.BLOCK, "OUTPUT_POLICY_BLOCKED", "EMPTY_OUTPUT")
    if len(text) > max_chars:
        return TextDecision(Decision.BLOCK, "OUTPUT_POLICY_BLOCKED", "OUTPUT_TOO_LONG")
    policy = check_input_policy(text, profile=profile)
    if policy.decision == Decision.BLOCK:
        return TextDecision(Decision.BLOCK, "OUTPUT_POLICY_BLOCKED", policy.reason_code,
                              matched_rules=policy.matched_rules)
    # Ordinary personal-data patterns are transformed in the following mandatory
    # masking action. Never return the unmasked intermediate output.
    return TextDecision()
