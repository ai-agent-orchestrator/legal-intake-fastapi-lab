from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    TRANSFORM = "TRANSFORM"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class ActionDecision:
    decision: Decision = Decision.ALLOW
    reason_code: str = "SAFE"
    detail_code: str | None = None
    safe_text: str | None = None
    matched_rules: tuple[str, ...] = ()
    reservation_id: str | None = None


class SecurityError(Exception):
    def __init__(self, code: str, status: int = 503):
        self.code, self.status = code, status
        super().__init__(code)


class PolicyBlocked(Exception):
    def __init__(self, decision: ActionDecision):
        self.decision = decision
        super().__init__(decision.reason_code)
