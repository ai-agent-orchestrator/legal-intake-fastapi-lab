import asyncio
from contextlib import asynccontextmanager

from app.security.decisions import SecurityError


class AdmissionManager:
    """Bounded, single-event-loop queue. No await between owning/releasing and counters."""
    def __init__(self, concurrent: int, waiters: int, timeout: float):
        self.limit, self.max_waiters, self.timeout = concurrent, waiters, timeout
        self.active = self.waiting = 0
        self._semaphore = asyncio.Semaphore(concurrent)

    @asynccontextmanager
    async def lease(self):
        waiting = self._semaphore.locked()
        if waiting and self.waiting >= self.max_waiters:
            raise SecurityError("GENERATION_CAPACITY_EXCEEDED")
        if waiting:
            self.waiting += 1
        try:
            try:
                async with asyncio.timeout(self.timeout):
                    await self._semaphore.acquire()
            except TimeoutError:
                raise SecurityError("GENERATION_CAPACITY_EXCEEDED") from None
        finally:
            if waiting:
                self.waiting -= 1
        self.active += 1
        try:
            yield
        finally:
            self.active -= 1
            self._semaphore.release()
