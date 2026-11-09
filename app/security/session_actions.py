"""L02: context, session blocks, and confirmed user-input policy risk events."""
from collections import deque
from threading import Lock
from app.security.context import Envelope, RequestContext, fingerprint
from app.security.decisions import ActionDecision, Decision, SecurityError
from app.security.risk_store import RiskStore

# Technical failures, capacity, budget, REVIEW, and repeated session blocks are not attacks.
RISK_REASONS = frozenset({
    "PROMPT_INJECTION", "JAILBREAK", "SECRET_REQUEST", "PRIVACY_REQUEST",
    "LEGAL_ABUSE",
    "BLOCKED_JAILBREAK", "BLOCKED_PROMPT_INJECTION", "BLOCKED_SECRET_REQUEST",
    "BLOCKED_PRIVACY_RISK", "BLOCKED_AUTH_BYPASS", "BLOCKED_LEGAL_HARM",
})


class SessionRiskActions:
    def __init__(self, store: RiskStore):
        self.store = store
        # Audit metadata only: never retain request text, identities, or secrets.
        self.audit_events: deque[dict] = deque(maxlen=1000)
        self._audit_lock = Lock()

    def validate_request_context(self, source: Envelope, *, expected: RequestContext) -> ActionDecision:
        context = source.context
        if (not isinstance(expected, RequestContext) or context != expected
                or not all((context.trace_id, context.session_id, context.snapshot,
                            context.profile, context.policy_version))
                or fingerprint(source.text) != source.digest):
            raise SecurityError("REQUEST_CONTEXT_MISMATCH", 500)
        return ActionDecision()

    def check_session_risk(self, source: Envelope) -> ActionDecision:
        if self.store.blocked(source.context.session_id):
            return ActionDecision(Decision.BLOCK, "DYNAMIC_SESSION_BLOCKED")
        return ActionDecision()

    def record_risk_event(self, source: Envelope, *, stage: str, reason: str) -> ActionDecision:
        if stage in {"output", "retrieved"}:
            with self._audit_lock:
                self.audit_events.append({"traceId": source.context.trace_id,
                                          "stage": stage, "reasonCode": reason})
            return ActionDecision(detail_code="NON_POLICY_EVENT")
        if reason not in RISK_REASONS:
            return ActionDecision(detail_code="NON_POLICY_EVENT")
        if stage != "input":
            raise SecurityError("GUARDRAIL_INVALID_EVENT")
        recorded = self.store.record(source.context.session_id, source.context.trace_id, stage, reason)
        return ActionDecision(detail_code="RECORDED" if recorded else "DUPLICATE_OR_BLOCKED")

    def registry(self):
        return {"validate_request_context": self.validate_request_context,
                "check_session_risk": self.check_session_risk,
                "record_risk_event": self.record_risk_event}
