import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.dependencies import get_llm_client
from app.main import create_app
from app.security.context import Envelope, RequestContext
from app.security.decisions import Decision, PolicyBlocked, SecurityError
from app.security.nemo_adapter import NemoAdapter
from app.security.risk_store import RiskStore
from app.security.session_actions import SessionRiskActions
from app.security.session_guard import ContextSessionGuard
from app.services.guidance_service import GuidanceService

BACKENDS = ["local", pytest.param("nemo", marks=pytest.mark.nemo)]
BODY = {"clientName": "합성 의뢰인", "caseType": "CIVIL", "coreStatement": "상담 준비 자료"}


def guard_for(backend, store=None):
    store = store or RiskStore(60, 10, 3)
    return ContextSessionGuard(NemoAdapter(SessionRiskActions(store).registry(), backend)), store


def envelope(session="same", text="합성 본문"):
    context = RequestContext.create(session, "intake:1:snapshot", "guidance")
    return Envelope.bind(context, text)


@pytest.mark.parametrize("backend", BACKENDS)
def test_threshold_dedup_normalization_and_session_isolation(backend):
    async def scenario():
        guard, store = guard_for(backend)
        source = envelope(" same ")
        for _ in range(3):
            await guard.record(source.context, source, stage="input", reason="PROMPT_INJECTION")
        assert len(store.events) == 1
        await guard.begin(source.context, source)
        for _ in range(2):
            item = envelope("same")
            await guard.record(item.context, item, stage="input", reason="PROMPT_INJECTION")
        with pytest.raises(PolicyBlocked) as blocked:
            await guard.begin(source.context, source)
        assert blocked.value.decision.reason_code == "DYNAMIC_SESSION_BLOCKED"
        assert len(store.events) == 3
        other = envelope("other")
        assert (await guard.begin(other.context, other)).text == other.text
        with patch("app.security.risk_store.monotonic", return_value=10**15):
            await guard.begin(source.context, source)
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("field,value", [
    ("trace_id", "another-request"), ("session_id", "another-session"),
    ("snapshot", "intake:2:v1"), ("profile", "another-profile"),
    ("policy_version", "another-policy"),
])
def test_foreign_or_stale_response_is_rejected(backend, field, value):
    async def scenario():
        guard, store = guard_for(backend)
        expected = envelope()
        foreign = Envelope.bind(replace(expected.context, **{field: value}), "foreign private response")
        with pytest.raises(SecurityError, match="REQUEST_CONTEXT_MISMATCH") as error:
            await guard.publish(expected.context, foreign)
        assert error.value.status == 500
        assert "private" not in str(error.value)
        assert not store.events
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_empty_context_and_tampered_body_fail_without_risk(backend):
    async def scenario():
        guard, store = guard_for(backend)
        source = envelope()
        with pytest.raises(SecurityError, match="REQUEST_CONTEXT_MISMATCH"):
            await guard.begin(source.context, replace(source, text="tampered"))
        empty = replace(source.context, trace_id="")
        with pytest.raises(SecurityError, match="REQUEST_CONTEXT_MISMATCH"):
            await guard.begin(empty, Envelope.bind(empty, "body"))
        assert not store.events
    asyncio.run(scenario())


def test_missing_and_blank_sessions_are_request_local():
    sources = [envelope(None), envelope(None), envelope(""), envelope(" ")]
    assert len({s.context.session_id for s in sources}) == 4
    assert len({s.context.trace_id for s in sources}) == 4
    assert envelope(" same ").context.session_id == envelope("same").context.session_id


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("reason", ["COST_LIMIT_BLOCKED", "GENERATION_CAPACITY_EXCEEDED", "MARKETING_REVIEW_REQUIRED",
                                      "GUARDRAIL_UNAVAILABLE", "DYNAMIC_SESSION_BLOCKED", "REQUEST_CONTEXT_MISMATCH"])
def test_non_policy_events_do_not_change_risk(backend, reason):
    async def scenario():
        guard, store = guard_for(backend)
        source = envelope()
        receipt = await guard.record(source.context, source, stage="input", reason=reason)
        assert receipt.decision.detail_code == "NON_POLICY_EVENT"
        assert not store.events and not store.blocked(source.context.session_id)
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_risk_capacity_errors_are_technical_and_do_not_evict_blocks(backend):
    async def scenario():
        guard, store = guard_for(backend, RiskStore(60, 1, 1))
        first, second = envelope("first"), envelope("second")
        await guard.record(first.context, first, stage="input", reason="PROMPT_INJECTION")
        with pytest.raises(SecurityError, match="RISK_STORE_CAPACITY_EXCEEDED") as error:
            await guard.record(second.context, second, stage="input", reason="PROMPT_INJECTION")
        assert error.value.status == 503
        assert store.blocked(first.context.session_id) and len(store.events) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_guidance_block_avoids_provider_and_other_sessions_continue(backend):
    application = create_app(Settings(_env_file=None, fake_llm=True, fake_llm_delay_seconds=0, guardrail_backend=backend))
    provider = SimpleNamespace(model="test", ask=AsyncMock(return_value="검토할 자료를 정리하세요."))
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        key = client.post("/api/intakes", json=BODY).json()["intakeId"]
        store = application.state.risk_store
        context = RequestContext.create("blocked-session", "seed", "guidance")
        for index in range(3):
            store.record(context.session_id, f"confirmed-policy-{index}", "input", "PROMPT_INJECTION")
        response = client.post(f"/api/intakes/{key}/guidance", headers={"X-Session-ID": "blocked-session"})
        assert response.status_code == 200 and response.json()["blocked"]
        assert response.json()["reasonCode"] == "DYNAMIC_SESSION_BLOCKED"
        provider.ask.assert_not_awaited()
        response = client.post(f"/api/intakes/{key}/guidance", headers={"X-Session-ID": "other-session"})
        assert response.status_code == 200 and response.json()["answer"] == "검토할 자료를 정리하세요."
        provider.ask.assert_awaited_once()
        assert len(store.events) == 3


@pytest.mark.parametrize("backend", BACKENDS)
def test_foreign_generated_response_returns_sanitized_500(backend, monkeypatch):
    application = create_app(Settings(_env_file=None, fake_llm=True, guardrail_backend=backend))
    async def foreign(self, source):
        return Envelope.bind(RequestContext.create("foreign", "other:snapshot", "guidance"), "private answer")
    monkeypatch.setattr(GuidanceService, "_generate", foreign)
    with TestClient(application) as client:
        key = client.post("/api/intakes", json=BODY).json()["intakeId"]
        response = client.post(f"/api/intakes/{key}/guidance")
        assert response.status_code == 500 and response.json()["code"] == "REQUEST_CONTEXT_MISMATCH"
        assert "private" not in response.text and not application.state.risk_store.events


@pytest.mark.parametrize("backend", BACKENDS)
def test_nemo_action_failure_returns_503_without_calling_provider(backend, monkeypatch):
    application = create_app(Settings(_env_file=None, fake_llm=True, guardrail_backend=backend))
    original = SessionRiskActions.check_session_risk
    def failure(self, source):
        # Registration now checks the session too; inject failure specifically at
        # guidance, the boundary this regression has always exercised.
        if source.context.profile != "guidance":
            return original(self, source)
        raise RuntimeError("private body and key")
    monkeypatch.setattr(SessionRiskActions, "check_session_risk", failure)
    provider = SimpleNamespace(model="test", ask=AsyncMock())
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        key = client.post("/api/intakes", json=BODY).json()["intakeId"]
        response = client.post(f"/api/intakes/{key}/guidance")
        assert response.status_code == 503 and response.json()["code"] == "GUARDRAIL_UNAVAILABLE"
        assert "private" not in response.text
        provider.ask.assert_not_awaited()
        assert not application.state.risk_store.events


@pytest.mark.parametrize("backend", BACKENDS)
def test_overlapping_guidance_keeps_a_b_separate(backend):
    async def scenario():
        application = create_app(Settings(_env_file=None, fake_llm=True, guardrail_backend=backend))
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0
        async def ask(instructions, prompt):
            nonlocal calls
            import json
            calls += 1
            if calls == 2:
                entered.set()
            await release.wait()
            return json.loads(prompt)["coreStatement"]
        application.dependency_overrides[get_llm_client] = lambda: SimpleNamespace(model="test", ask=ask)
        async with application.router.lifespan_context(application):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
                ids = []
                for body in ("합성 A", "합성 B"):
                    ids.append((await client.post("/api/intakes", json={**BODY, "coreStatement": body})).json()["intakeId"])
                tasks = [asyncio.create_task(client.post(f"/api/intakes/{key}/guidance",
                         headers={"X-Session-ID": "same"})) for key in ids]
                try:
                    await asyncio.wait_for(entered.wait(), 5)
                    assert (await client.get(f"/api/intakes/{ids[0]}")).status_code == 200
                    release.set()
                    responses = await asyncio.wait_for(asyncio.gather(*tasks), 5)
                    assert [r.json()["answer"] for r in responses] == ["합성 A", "합성 B"]
                finally:
                    release.set()
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.run(scenario())


def test_invalid_session_header_does_not_call_provider():
    application = create_app(Settings(_env_file=None, fake_llm=True))
    provider = SimpleNamespace(model="test", ask=AsyncMock())
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        key = client.post("/api/intakes", json=BODY).json()["intakeId"]
        for session in (" ", "a" * 129):
            assert client.post(f"/api/intakes/{key}/guidance", headers={"X-Session-ID": session}).status_code == 422
        provider.ask.assert_not_awaited()
