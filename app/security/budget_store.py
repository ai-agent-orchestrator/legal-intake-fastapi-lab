from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from uuid import uuid4


@dataclass
class Reservation:
    amount: Decimal
    state: str = "OPEN"
    charged: Decimal = Decimal(0)


class BudgetStore:
    """Single-process USD ledger. Mutation has no await points, including cleanup."""
    def __init__(self, limit: Decimal):
        if not limit.is_finite() or limit < 0:
            raise ValueError("invalid budget limit")
        self.limit, self.spent = limit, Decimal(0)
        self.reservations: dict[str, Reservation] = {}
        self._lock = Lock()

    def reserve(self, amount: Decimal) -> str | None:
        if not amount.is_finite() or amount < 0:
            raise ValueError("invalid reservation")
        with self._lock:
            pending = sum((r.amount for r in self.reservations.values() if r.state == "OPEN"), Decimal(0))
            if self.spent + pending + amount > self.limit:
                return None
            key = uuid4().hex
            self.reservations[key] = Reservation(amount)
            return key

    def settle(self, key: str, state: str, actual: Decimal | None = None) -> bool:
        if state not in {"REPORTED", "ESTIMATED", "RELEASED"}:
            raise ValueError("invalid settlement")
        if actual is not None and (not actual.is_finite() or actual < 0):
            raise ValueError("invalid usage")
        with self._lock:
            row = self.reservations[key]
            if row.state != "OPEN":
                return False
            row.state = state
            row.charged = Decimal(0) if state == "RELEASED" else (actual if actual is not None else row.amount)
            self.spent += row.charged
            # Bound retained receipts; OPEN reservations are never discarded.
            if len(self.reservations) > 2000:
                for old in list(self.reservations):
                    if old != key and self.reservations[old].state != "OPEN":
                        del self.reservations[old]
                        break
            return True
