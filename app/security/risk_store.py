from collections import OrderedDict, deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic


@dataclass
class Risk:
    expires: float
    events: set[tuple[str, str]] = field(default_factory=set)


class RiskStore:
    def __init__(self, ttl: float, capacity: int, threshold: int):
        self.ttl, self.capacity, self.threshold = ttl, capacity, threshold
        self._rows: OrderedDict[str, Risk] = OrderedDict()
        self.events: deque[dict] = deque(maxlen=1000)
        self._lock = Lock()

    def _expire(self):
        now = monotonic()
        for key in list(self._rows):
            if self._rows[key].expires <= now:
                del self._rows[key]

    def blocked(self, session: str) -> bool:
        with self._lock:
            self._expire()
            row = self._rows.get(session)
            return row is not None and len(row.events) >= self.threshold

    def record(self, session: str, trace: str, stage: str, reason: str) -> bool:
        with self._lock:
            self._expire()
            if session not in self._rows:
                if len(self._rows) >= self.capacity:
                    # Fail closed: do not evict a still-blocked session to admit a new one.
                    from app.security.decisions import SecurityError
                    raise SecurityError("RISK_STORE_CAPACITY_EXCEEDED")
                self._rows[session] = Risk(monotonic() + self.ttl)
            row = self._rows[session]
            event = (trace, stage)
            if event in row.events or len(row.events) >= self.threshold:
                return False
            row.events.add(event)
            self.events.append({"traceId": trace, "stage": stage, "reasonCode": reason})
            return True
