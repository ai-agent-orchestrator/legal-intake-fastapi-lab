import asyncio
from decimal import Decimal

from app.core.exceptions import AiRequestError
from app.security.admission import AdmissionManager
from app.security.budget_store import BudgetStore
from app.security.context import Envelope
from app.security.decisions import Decision, PolicyBlocked, SecurityError
from app.security.nemo_adapter import NemoAdapter
from app.security.resource_actions import BudgetTicket


class PaidCallService:
    def __init__(self, adapter: NemoAdapter, admission: AdmissionManager, budget: BudgetStore,
                 reservation_usd: Decimal, timeout: float):
        self.adapter, self.admission, self.budget = adapter, admission, budget
        self.reservation_usd, self.timeout = reservation_usd, timeout

    async def call(self, source: Envelope, client, instructions: str) -> str:
        amount = self.reservation_usd
        estimate = getattr(client, "reservation_estimate", None)
        if callable(estimate):
            required = estimate(instructions, source.text)
            if not isinstance(required, Decimal) or not required.is_finite() or required < 0:
                raise SecurityError("BUDGET_INVALID_RESERVATION")
            amount = max(amount, required)
        ticket = BudgetTicket(amount)
        started = False
        actual = None
        async with self.admission.lease():
            try:
                await self.adapter.check("check_generation_admission", source)
                receipt = await self.adapter.check("check_request_budget", source, ticket=ticket)
                if receipt.decision.decision == Decision.BLOCK:
                    raise PolicyBlocked(receipt.decision)
                if ticket.reservation_id is None or receipt.decision.reservation_id != ticket.reservation_id:
                    raise SecurityError("BUDGET_INVALID_RESERVATION")
                async with asyncio.timeout(self.timeout):
                    started = True
                    answer = await client.ask(instructions, source.text)
                    reported = getattr(answer, "cost_usd", None)
                    if not isinstance(answer, str) or (reported is not None and (
                            not isinstance(reported, Decimal) or not reported.is_finite() or reported < 0)):
                        raise AiRequestError("AI 공급자 응답 형식이 올바르지 않습니다.")
                    actual = reported
                return answer
            except TimeoutError:
                raise AiRequestError("AI 안내 생성 대기 시간을 초과했습니다.") from None
            except AiRequestError as exc:
                # A response can include usage even when its output is unusable.
                if isinstance(exc.cost_usd, Decimal) and exc.cost_usd.is_finite() and exc.cost_usd >= 0:
                    actual = exc.cost_usd
                raise
            finally:
                # Synchronous, bounded cleanup has no cancellation point. It also
                # handles cancellation *inside* the reservation rail after mutation.
                if ticket.reservation_id is not None:
                    state = "RELEASED" if not started else "REPORTED" if actual is not None else "ESTIMATED"
                    self.budget.settle(ticket.reservation_id, state, actual)
