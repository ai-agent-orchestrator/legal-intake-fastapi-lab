import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx
from openai import APIConnectionError
import pytest

from app.clients.llm_client import OpenAiLlmClient
from app.core.config import Settings
from app.core.exceptions import AiRequestError
from app.dependencies import get_llm_client
from app.domain.intake import CaseType
from app.main import create_app
from app.repositories.intake_repository import IntakeRepository
from app.routers.intake_router import router


BODY = {"clientName": "연습의뢰인", "caseType": "CIVIL", "coreStatement": "보증금 반환 상담에 필요한 자료를 준비하려고 합니다."}


def fake_settings():
    return Settings(_env_file=None, fake_llm=True, fake_llm_delay_seconds=0)


@pytest.fixture
def application():
    return create_app(fake_settings())


@pytest.fixture
def client(application):
    with TestClient(application) as c:
        yield c


def register(client, body=None):
    response = client.post("/api/intakes", json=body or BODY)
    assert response.status_code == 201
    return response.json()["intakeId"]


def test_create_and_find_are_camel_case(client):
    intake_id = register(client)
    response = client.get(f"/api/intakes/{intake_id}")
    assert response.status_code == 200
    assert response.json() == {"intakeId": intake_id, **BODY, "desiredNextStep": None}


@pytest.mark.parametrize("changes", [
    {"clientName": " "}, {"clientName": "가" * 51}, {"caseType": "INVALID"},
    {"coreStatement": ""}, {"coreStatement": "가" * 101},
    {"desiredNextStep": "가" * 101}, {"unknown": "field"},
])
def test_invalid_requests_are_422(client, changes):
    assert client.post("/api/intakes", json={**BODY, **changes}).status_code == 422


def test_missing_required_field(client):
    assert client.post("/api/intakes", json={"caseType": "CIVIL"}).status_code == 422


def test_optional_step_and_whitespace(client):
    intake_id = register(client, {**BODY, "clientName": "  연습  ", "desiredNextStep": "  "})
    result = client.get(f"/api/intakes/{intake_id}").json()
    assert result["clientName"] == "연습" and result["desiredNextStep"] is None


def test_custom_404(client):
    response = client.get("/api/intakes/999")
    assert response.status_code == 404
    assert response.json()["code"] == "INTAKE_NOT_FOUND"


def test_non_integer_id_is_422(client):
    assert client.get("/api/intakes/not-a-number").status_code == 422


def test_missing_guidance_does_not_call_ai(client, application):
    recorder = SimpleNamespace(model="recording-fake", ask=AsyncMock())
    application.dependency_overrides[get_llm_client] = lambda: recorder
    assert client.post("/api/intakes/999/guidance").status_code == 404
    recorder.ask.assert_not_awaited()


def test_guidance_awaits_saved_facts_without_client_name(client, application):
    intake_id = register(client)
    recorder = SimpleNamespace(model="recording-fake", ask=AsyncMock(return_value="연습용 안내"))
    application.dependency_overrides[get_llm_client] = lambda: recorder
    response = client.post(f"/api/intakes/{intake_id}/guidance")
    assert response.status_code == 200
    assert response.json() == {"intakeId": intake_id, "answer": "연습용 안내", "model": "recording-fake"}
    recorder.ask.assert_awaited_once()
    instructions, prompt = recorder.ask.await_args.args
    facts = json.loads(prompt)
    assert facts["coreStatement"] == BODY["coreStatement"]
    assert facts["caseType"] == "CIVIL"
    assert "clientName" not in facts and BODY["clientName"] not in prompt
    assert "상담" in instructions


def test_fake_guidance_is_explicit(client):
    intake_id = register(client)
    response = client.post(f"/api/intakes/{intake_id}/guidance")
    assert response.status_code == 200
    assert response.json()["model"] == "fake-llm"


def test_provider_failure_is_502(client, application):
    intake_id = register(client)
    failure = SimpleNamespace(model="failing-fake", ask=AsyncMock(side_effect=AiRequestError("연습용 연결 실패")))
    application.dependency_overrides[get_llm_client] = lambda: failure
    response = client.post(f"/api/intakes/{intake_id}/guidance")
    assert response.status_code == 502 and response.json()["code"] == "AI_REQUEST_FAILED"


def test_execution_models_and_swagger(client):
    endpoints = {f"{method} {route.path}": inspect.iscoroutinefunction(route.endpoint)
                 for route in router.routes for method in route.methods}
    assert endpoints == {"POST /api/intakes": False, "GET /api/intakes/{intake_id}": False,
                         "POST /api/intakes/{intake_id}/guidance": True}
    assert client.get("/docs").status_code == 200
    assert len(client.get("/openapi.json").json()["paths"]) == 3


def test_repository_concurrent_ids():
    repository = IntakeRepository()
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda i: repository.save(f"연습{i}", CaseType.CIVIL, "연습 사실", None), range(50)))
    assert {row.intake_id for row in rows} == set(range(1, 51))


def test_restart_clears_memory(client):
    register(client)
    with TestClient(create_app(fake_settings())) as restarted:
        assert restarted.get("/api/intakes/1").status_code == 404


def test_real_mode_requires_key():
    settings = Settings(_env_file=None, fake_llm=False, openai_api_key=None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAiLlmClient(settings)


def test_sdk_failure_is_sanitized_without_network():
    sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(side_effect=APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")))), close=AsyncMock())
    settings = Settings(_env_file=None, fake_llm=False, openai_api_key="not-a-real-key")
    with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
        client = OpenAiLlmClient(settings)
        with pytest.raises(AiRequestError) as failure:
            asyncio.run(client.ask("지시", "내용"))
        assert "not-a-real-key" not in str(failure.value)
        asyncio.run(client.close())
        sdk.close.assert_awaited_once()


def test_empty_provider_response_is_502_error():
    sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(output_text=" "))), close=AsyncMock())
    settings = Settings(_env_file=None, fake_llm=False, openai_api_key="not-a-real-key")
    with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
        client = OpenAiLlmClient(settings)
        with pytest.raises(AiRequestError):
            asyncio.run(client.ask("지시", "내용"))
        asyncio.run(client.close())


def test_ai_waits_overlap_and_lookup_remains_responsive():
    async def scenario():
        application = create_app(fake_settings())
        all_started = asyncio.Event()
        release = asyncio.Event()

        class ControlledClient:
            model = "controlled-fake"
            calls = 0

            async def ask(self, instructions, prompt):
                self.calls += 1
                if self.calls == 2:
                    all_started.set()
                await release.wait()
                return json.loads(prompt)["coreStatement"]

        controlled = ControlledClient()
        application.dependency_overrides[get_llm_client] = lambda: controlled
        async with application.router.lifespan_context(application):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
                ids = []
                for message in ["연습 사건 A", "연습 사건 B"]:
                    response = await client.post("/api/intakes", json={**BODY, "coreStatement": message})
                    ids.append(response.json()["intakeId"])
                tasks = [asyncio.create_task(client.post(f"/api/intakes/{i}/guidance")) for i in ids]
                try:
                    await asyncio.wait_for(all_started.wait(), timeout=3)
                    lookup = await asyncio.wait_for(client.get(f"/api/intakes/{ids[0]}"), timeout=3)
                    assert lookup.status_code == 200
                    assert all(not task.done() for task in tasks)
                finally:
                    release.set()
                    responses = await asyncio.wait_for(asyncio.gather(*tasks), timeout=3)
                assert [r.json()["answer"] for r in responses] == ["연습 사건 A", "연습 사건 B"]

    asyncio.run(scenario())
