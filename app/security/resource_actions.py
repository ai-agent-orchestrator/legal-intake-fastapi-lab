"""Resource decisions; their service owns acquisition and unconditional cleanup."""
from dataclasses import dataclass
from decimal import Decimal

from app.security.admission import AdmissionManager
from app.security.budget_store import BudgetStore
from app.security.context import Envelope
from app.security.decisions import ActionDecision, Decision, SecurityError


@dataclass
class BudgetTicket:
    amount: Decimal
    reservation_id: str | None = None


class ResourceActions:
    def __init__(self, admission: AdmissionManager, budget: BudgetStore):
        self.admission, self.budget = admission, budget

    def check_generation_admission(self, source: Envelope) -> ActionDecision:
        # The service calls this inside the manager's lease, never instead of it.
        if not 0 < self.admission.active <= self.admission.limit:
            raise SecurityError("GENERATION_CAPACITY_EXCEEDED")
        return ActionDecision()

    def check_request_budget(self, source: Envelope, *, ticket: BudgetTicket) -> ActionDecision:
        if ticket.reservation_id is not None:
            raise SecurityError("BUDGET_ALREADY_RESERVED")
        ticket.reservation_id = self.budget.reserve(ticket.amount)
        if ticket.reservation_id is None:
            return ActionDecision(Decision.BLOCK, "COST_LIMIT_BLOCKED")
        # The ticket belongs to the service before awaiting the rail. If NeMo is
        # cancelled or rejects the receipt, finally still releases this reservation.
        return ActionDecision(reservation_id=ticket.reservation_id)

    def registry(self):
        return {"check_generation_admission": self.check_generation_admission,
                "check_request_budget": self.check_request_budget}
