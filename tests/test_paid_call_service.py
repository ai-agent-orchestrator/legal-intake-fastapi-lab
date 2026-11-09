import asyncio
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.clients.llm_client import GeneratedText
from app.core.exceptions import AiRequestError
from app.security.admission import AdmissionManager
from app.security.budget_store import BudgetStore
from app.security.context import Envelope, RequestContext
from app.security.decisions import PolicyBlocked, SecurityError
from app.security.nemo_adapter import NemoAdapter
from app.security.resource_actions import ResourceActions
from app.services.paid_call_service import PaidCallService


def resources(*, concurrent=1, waiters=1, wait_timeout=1, call_timeout=1, backend="local"):
    admission = AdmissionManager(concurrent, waiters, wait_timeout)
    budget = BudgetStore(Decimal("0.03"))
    adapter = NemoAdapter(ResourceActions(admission, budget).registry(), backend)
    service = PaidCallService(adapter, admission, budget, Decimal("0.01"), call_timeout)
    return service, admission, budget


def source():
    return Envelope.bind(RequestContext.create("synthetic", "synthetic:1", "guidance"), "합성 상담 준비")


async def wait_until(predicate):
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0)


@pytest.mark.parametrize("backend", ["local", pytest.param("nemo", marks=pytest.mark.nemo)])
@pytest.mark.parametrize("kind,state,charged", [
    ("known", "REPORTED", "0.002"), ("unknown", "ESTIMATED", "0.01"),
    ("failure", "ESTIMATED", "0.01"), ("timeout", "ESTIMATED", "0.01"),
    ("cancel", "ESTIMATED", "0.01"), ("invalid_usage", "ESTIMATED", "0.01"),
])
def test_settlement_and_slot_release_on_every_call_exit(backend, kind, state, charged):
    async def scenario():
        service, admission, budget = resources(call_timeout=0.02 if kind == "timeout" else 3, backend=backend)
        entered = asyncio.Event()
        async def ask(instructions, prompt):
            assert admission.active == 1 and sum(r.state == "OPEN" for r in budget.reservations.values()) == 1
            entered.set()
            if kind in {"timeout", "cancel"}:
                await asyncio.Event().wait()
            if kind == "failure":
                raise AiRequestError("synthetic failure")
            if kind == "known":
                return GeneratedText("상담 준비", Decimal("0.002"))
            if kind == "invalid_usage":
                return GeneratedText("상담 준비", Decimal("NaN"))
            return "상담 준비"
        task = asyncio.create_task(service.call(source(), SimpleNamespace(ask=ask), "준비 안내"))
        if kind == "cancel":
            await asyncio.wait_for(entered.wait(), 3)
            task.cancel()
        if kind == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await task
        elif kind in {"failure", "timeout", "invalid_usage"}:
            with pytest.raises(AiRequestError):
                await task
        else:
            assert await task == "상담 준비"
        assert admission.active == admission.waiting == 0
        assert len(budget.reservations) == 1
        row = next(iter(budget.reservations.values()))
        assert row.state == state and row.charged == budget.spent == Decimal(charged)
    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["cancel", "bad_receipt", "exception"])
@pytest.mark.parametrize("backend", ["local", pytest.param("nemo", marks=pytest.mark.nemo)])
def test_reservation_rail_failure_releases_money_even_without_receipt(fault, backend):
    async def scenario():
        service, admission, budget = resources(backend=backend)
        original = service.adapter.check
        entered = asyncio.Event()
        async def check(name, envelope, **kwargs):
            receipt = await original(name, envelope, **kwargs)
            if name == "check_request_budget":
                entered.set()
                if fault == "cancel":
                    await asyncio.Event().wait()
                raise SecurityError("GUARDRAIL_INVALID_DECISION" if fault == "bad_receipt" else "GUARDRAIL_UNAVAILABLE")
            return receipt
        service.adapter.check = check
        provider = SimpleNamespace(ask=AsyncMock())
        task = asyncio.create_task(service.call(source(), provider, "準備"))
        if fault == "cancel":
            await asyncio.wait_for(entered.wait(), 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(SecurityError):
                await task
        provider.ask.assert_not_awaited()
        assert admission.active == admission.waiting == 0 and budget.spent == 0
        assert [r.state for r in budget.reservations.values()] == ["RELEASED"]
    asyncio.run(scenario())


def test_queue_limit_waiter_cancellation_and_no_early_budget_reservation():
    async def scenario():
        service, admission, budget = resources()
        entered, release = asyncio.Event(), asyncio.Event()
        async def ask(instructions, prompt):
            entered.set()
            await release.wait()
            return "상담 준비"
        provider = SimpleNamespace(ask=ask)
        first = asyncio.create_task(service.call(source(), provider, "준비"))
        second = None
        try:
            await asyncio.wait_for(entered.wait(), 3)
            second = asyncio.create_task(service.call(source(), provider, "준비"))
            await wait_until(lambda: admission.waiting == 1)
            assert admission.active == 1 and len(budget.reservations) == 1
            with pytest.raises(SecurityError, match="GENERATION_CAPACITY_EXCEEDED"):
                await service.call(source(), provider, "준비")
            second.cancel()
            with pytest.raises(asyncio.CancelledError):
                await second
            assert admission.waiting == 0 and len(budget.reservations) == 1
            release.set()
            await first
            assert await service.call(source(), provider, "준비") == "상담 준비"
            assert admission.active == admission.waiting == 0
        finally:
            release.set()
            first.cancel()
            if second:
                second.cancel()
            await asyncio.gather(first, *([second] if second else []), return_exceptions=True)
    asyncio.run(scenario())


def test_wait_timeout_does_not_reserve_or_leak_capacity():
    async def scenario():
        service, admission, budget = resources(wait_timeout=0.01)
        async with admission.lease():
            provider = SimpleNamespace(ask=AsyncMock())
            with pytest.raises(SecurityError, match="GENERATION_CAPACITY_EXCEEDED"):
                await service.call(source(), provider, "준비")
            provider.ask.assert_not_awaited()
            assert admission.active == 1 and admission.waiting == 0 and not budget.reservations
        assert admission.active == 0
    asyncio.run(scenario())


def test_concurrent_calls_cannot_overspend_remaining_reservation_budget():
    async def scenario():
        service, admission, budget = resources(concurrent=4)
        release = asyncio.Event()
        async def ask(instructions, prompt):
            await release.wait()
            return "상담 준비"
        tasks = [asyncio.create_task(service.call(source(), SimpleNamespace(ask=ask), "준비")) for _ in range(4)]
        try:
            await wait_until(lambda: len(budget.reservations) == 3 and any(t.done() for t in tasks))
            assert admission.active == 3
            release.set()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            assert sum(isinstance(r, PolicyBlocked) for r in results) == 1
            assert budget.spent == Decimal("0.03")
            assert admission.active == admission.waiting == 0
        finally:
            release.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.run(scenario())


def test_atomic_reservation_and_single_settlement_across_threads():
    budget = BudgetStore(Decimal("0.02"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(lambda _: budget.reserve(Decimal("0.01")), range(20)))
    reserved = [key for key in keys if key is not None]
    assert len(reserved) == 2
    with ThreadPoolExecutor(max_workers=8) as pool:
        changed = list(pool.map(lambda _: budget.settle(reserved[0], "ESTIMATED"), range(20)))
    assert sum(changed) == 1 and budget.spent == Decimal("0.01")
