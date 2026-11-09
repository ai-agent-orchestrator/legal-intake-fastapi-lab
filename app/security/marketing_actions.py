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
    except Exception:
        # Keep the same technical error as the NeMo wrapper, also for direct
        # callers. Never expose an unexpected exception's draft or fall back.
        raise SecurityError("GUARDRAIL_UNAVAILABLE") from None

    # A buggy/replaced checker must not turn an unchecked value into a receipt.
    if not isinstance(result, marketing_core.MarketingDecision):
        raise SecurityError("GUARDRAIL_INVALID_DECISION")
    if (not isinstance(result.decision, marketing_core.Decision)
            or not isinstance(result.safe_draft, str) or not result.safe_draft.strip()
            or len(result.safe_draft) > marketing_core.MAX_OUTPUT_CHARS
            or not isinstance(result.review_required, bool)
            or result.rule_version != marketing_core.RULE_VERSION
            or not isinstance(result.matched_rules, tuple)
            or any(not isinstance(rule, str) or rule not in marketing_core.RULE_IDS
                   for rule in result.matched_rules)):
        raise SecurityError("GUARDRAIL_INVALID_DECISION")
    if result.decision == marketing_core.Decision.ALLOW:
        valid = (not result.review_required and result.reason_code == "SAFE"
                 and not result.matched_rules and result.safe_draft == source.text)
    else:
        valid = (result.review_required and result.reason_code == "MARKETING_REVIEW_REQUIRED"
                 and bool(result.matched_rules) and result.safe_draft != source.text)
    if not valid:
        raise SecurityError("GUARDRAIL_INVALID_DECISION")
    return ActionDecision(Decision(result.decision.value), result.reason_code,
                          result.rule_version, result.safe_draft, result.matched_rules)


def marketing_registry():
    return {"check_marketing_response": check_marketing_response}
