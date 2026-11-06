from app.security.context import Envelope, RequestContext
from app.security.decisions import Decision, PolicyBlocked
from app.security.nemo_adapter import NemoAdapter, RailDirection


class ContextSessionGuard:
    def __init__(self, adapter: NemoAdapter):
        self.adapter = adapter

    async def begin(self, expected: RequestContext, source: Envelope) -> Envelope:
        await self.adapter.check("validate_request_context", source, expected=expected)
        receipt = await self.adapter.check("check_session_risk", source)
        if receipt.decision.decision == Decision.BLOCK:
            raise PolicyBlocked(receipt.decision)
        return receipt.output

    async def publish(self, expected: RequestContext, generated: Envelope) -> str:
        # Validate the envelope supplied by the generation stage, not a newly rebound copy.
        receipt = await self.adapter.check("validate_request_context", generated,
                                           direction=RailDirection.OUTPUT, expected=expected)
        return receipt.output.text

    async def record(self, expected: RequestContext, source: Envelope, *, stage: str, reason: str):
        await self.adapter.check("validate_request_context", source, expected=expected)
        return await self.adapter.check("record_risk_event", source, stage=stage, reason=reason)
