"""Run explicitly with the security extra installed; no network/model generation required."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.security.context import Envelope, RequestContext
from app.security.decisions import ActionDecision, Decision, SecurityError
from app.security.nemo_adapter import NemoAdapter, RailDirection

BACKENDS = ["local", pytest.param("nemo", marks=pytest.mark.nemo)]

def source(text="합성 원문"):
    return Envelope.bind(RequestContext.create("synthetic", "intake:1:v1", "guidance"), text)


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("direction", list(RailDirection))
@pytest.mark.parametrize("decision", list(Decision))
def test_real_rails_consume_all_decisions(backend, direction, decision):
    async def scenario():
        expected = source()
        action = AsyncMock(return_value=ActionDecision(decision, "TEST_POLICY", safe_text="검사 완료 본문"))
        adapter = NemoAdapter({"test_policy": action}, backend)
        receipt = await adapter.check("test_policy", expected, direction=direction)
        action.assert_awaited_once_with(expected)
        assert receipt.source is expected
        assert receipt.output.context == expected.context
        assert receipt.decision.decision == decision
        assert receipt.output.text == ("요청을 처리할 수 없습니다." if decision == Decision.BLOCK
                                       else "검사 완료 본문" if decision in {Decision.TRANSFORM, Decision.REVIEW}
                                       else expected.text)
        if backend == "nemo":
            assert not adapter._rails.events_history_cache
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_failure_is_technical_error_not_policy_block(backend):
    async def scenario():
        action = AsyncMock(side_effect=RuntimeError("private content and key"))
        adapter = NemoAdapter({"test_policy": action}, backend)
        with pytest.raises(SecurityError, match="GUARDRAIL_UNAVAILABLE") as error:
            await adapter.check("test_policy", source())
        assert "private" not in str(error.value)
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_concurrent_requests_are_isolated_and_cancellation_recovers(backend):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        count = 0
        async def action(envelope):
            nonlocal count
            count += 1
            if count == 2:
                entered.set()
            await release.wait()
            return ActionDecision(Decision.TRANSFORM, safe_text=envelope.text + " 검사 완료")
        adapter = NemoAdapter({"test_policy": action}, backend)
        a, b = source("A"), source("B")
        tasks = [asyncio.create_task(adapter.check("test_policy", item)) for item in (a, b)]
        try:
            await asyncio.wait_for(entered.wait(), 5)
            tasks[0].cancel()
            with pytest.raises(asyncio.CancelledError):
                await tasks[0]
            release.set()
            result = await asyncio.wait_for(tasks[1], 5)
            assert result.output.text == "B 검사 완료" and result.source is b
            assert (await adapter.check("test_policy", a)).output.text == "A 검사 완료"
        finally:
            release.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.run(scenario())


def test_missing_or_corrupt_binding_fails_before_action():
    async def scenario():
        action = AsyncMock(return_value=ActionDecision())
        adapter = NemoAdapter({"test_policy": action})
        with pytest.raises(SecurityError, match="GUARDRAIL_NOT_CONFIGURED"):
            await adapter.check("missing", source())
        with pytest.raises(SecurityError, match="REQUEST_CONTEXT_MISMATCH"):
            await adapter.check("test_policy", replace(source(), text="tampered"))
        action.assert_not_awaited()
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("result", [None, {}, ActionDecision(Decision.TRANSFORM), ActionDecision(Decision.REVIEW)])
def test_invalid_decisions_fail_closed(backend, result):
    async def scenario():
        adapter = NemoAdapter({"test_policy": AsyncMock(return_value=result)}, backend)
        with pytest.raises(SecurityError, match="GUARDRAIL_INVALID_DECISION"):
            await adapter.check("test_policy", source())
    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["missing_action", "duplicate_action", "wrong_status", "wrong_text"])
def test_runtime_must_consume_exactly_one_action_and_its_result(fault):
    async def scenario():
        adapter = NemoAdapter({"test_policy": AsyncMock(return_value=ActionDecision())})
        async def faulty_runtime(messages):
            if fault != "missing_action":
                await adapter._dispatch()
            if fault == "duplicate_action":
                await adapter._dispatch()
            return SimpleNamespace(status=SimpleNamespace(value="blocked" if fault == "wrong_status" else "passed"),
                                   content="wrong" if fault == "wrong_text" else messages[0]["content"])
        adapter._rails = SimpleNamespace(check_async=faulty_runtime)
        with pytest.raises(SecurityError, match="GUARDRAIL_INVALID_DECISION"):
            await adapter.check("test_policy", source())
    asyncio.run(scenario())


def test_unavailable_nemo_never_falls_back_to_local(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "nemoguardrails", None)
    with pytest.raises(SecurityError, match="GUARDRAIL_UNAVAILABLE"):
        NemoAdapter({"test_policy": AsyncMock(return_value=ActionDecision())}, "nemo")
