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

    async def protect_input(self, expected: RequestContext, source: Envelope) -> Envelope:
        await self.adapter.check("validate_request_context", source, expected=expected)
        receipt = await self.adapter.check("check_input_policy", source)
        if receipt.decision.decision == Decision.BLOCK:
            await self.record(expected, source, stage="input", reason=receipt.decision.reason_code)
            raise PolicyBlocked(receipt.decision)
        return await self._mask(receipt.output)

    async def protect_output(self, expected: RequestContext, generated: Envelope) -> Envelope:
        await self.adapter.check("validate_request_context", generated,
                                 direction=RailDirection.OUTPUT, expected=expected)
        receipt = await self.adapter.check("check_output_policy", generated, direction=RailDirection.OUTPUT)
        if receipt.decision.decision == Decision.BLOCK:
            await self.record(expected, generated, stage="output", reason=receipt.decision.reason_code)
            raise PolicyBlocked(receipt.decision)
        return await self._mask(receipt.output, direction=RailDirection.OUTPUT)

    async def mask_stored_output(self, expected: RequestContext, source: Envelope) -> Envelope:
        await self.adapter.check("validate_request_context", source,
                                 direction=RailDirection.OUTPUT, expected=expected)
        return await self._mask(source, direction=RailDirection.OUTPUT)

    async def _mask(self, source: Envelope, *, direction=RailDirection.INPUT) -> Envelope:
        receipt = await self.adapter.check("mask_personal_data", source, direction=direction)
        if receipt.decision.decision == Decision.BLOCK:
            raise PolicyBlocked(receipt.decision)
        return receipt.output

    async def record(self, expected: RequestContext, source: Envelope, *, stage: str, reason: str):
        await self.adapter.check("validate_request_context", source, expected=expected)
        return await self.adapter.check("record_risk_event", source, stage=stage, reason=reason)
