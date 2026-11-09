"""Thin app/NeMo adapters for the independently reusable policy_core module."""
from app.security.context import Envelope
from app.security.decisions import ActionDecision, Decision, SecurityError
from app.security import policy_core

MASKING_VERSION = policy_core.MASKING_VERSION


def _run(function, source, **kwargs):
    if not isinstance(source, Envelope):
        raise SecurityError("GUARDRAIL_INVALID_INPUT")
    try:
        result = function(source.text, **kwargs)
    except policy_core.PolicyError as error:
        raise SecurityError(error.code) from None
    return ActionDecision(Decision(result.decision.value), result.reason_code,
                          result.detail_code, result.safe_text, result.matched_rules)


def check_input_policy(source: Envelope) -> ActionDecision:
    return _run(policy_core.check_input_policy, source, profile=source.context.profile)


def mask_personal_data(source: Envelope) -> ActionDecision:
    return _run(policy_core.mask_personal_data, source)


def check_output_policy(source: Envelope, *, max_chars: int = 8000) -> ActionDecision:
    return _run(policy_core.check_output_policy, source,
                max_chars=max_chars, profile=source.context.profile)


def policy_registry():
    return {"check_input_policy": check_input_policy, "mask_personal_data": mask_personal_data,
            "check_output_policy": check_output_policy}
