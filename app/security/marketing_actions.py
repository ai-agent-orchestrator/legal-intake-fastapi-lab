"""Thin envelope adapter; the reusable wording policy has no app dependencies."""
from app.security import marketing_core
from app.security.context import Envelope
from app.security.decisions import ActionDecision, Decision, SecurityError


def check_marketing_response(source: Envelope) -> ActionDecision:
    if not isinstance(source, Envelope):
        raise SecurityError("GUARDRAIL_INVALID_INPUT")
    try:
        result = marketing_core.check_marketing_response(source.text)
    except marketing_core.MarketingError:
        raise SecurityError("MARKETING_CHECK_UNAVAILABLE") from None
    return ActionDecision(Decision(result.decision.value), result.reason_code, result.rule_version,
                          result.safe_draft, result.matched_rules)


def marketing_registry():
    return {"check_marketing_response": check_marketing_response}
