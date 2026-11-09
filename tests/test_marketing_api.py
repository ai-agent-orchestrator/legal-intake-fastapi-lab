import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import httpx
import pytest

from app.core.config import Settings
from app.dependencies import get_llm_client
from app.main import create_app, create_full_app
from app.security import marketing_core

BACKENDS = ["local", pytest.param("nemo", marks=pytest.mark.nemo)]
POST = {"title": "합성 상담 안내", "content": "상담 준비 자료"}
REVIEW = {"rating": 3, "content": "합성 상담 서비스 경험"}


def application_for(backend="local", **settings):
    return create_full_app(Settings(_env_file=None, fake_llm=True, fake_llm_delay_seconds=0,
                                    guardrail_backend=backend, **settings))


def seed(client, rating=3):
    post = client.post("/api/posts", json=POST)
    assert post.status_code == 201, post.text
    post_id = post.json()["postId"]
    review = client.post(f"/api/posts/{post_id}/reviews", json={**REVIEW, "rating": rating})
    assert review.status_code == 201, review.text
    return post_id, review.json()["reviewId"]


def test_serving_has_exactly_eleven_operations_and_mvp_factory_stays_three():
    expected = {("POST", "/api/intakes"), ("GET", "/api/intakes/{intake_id}"),
        ("POST", "/api/intakes/{intake_id}/guidance"), ("GET", "/health"),
        ("POST", "/api/posts"), ("GET", "/api/posts"), ("GET", "/api/posts/{postId}"),
        ("POST", "/api/posts/{postId}/reviews"), ("GET", "/api/posts/{postId}/reviews"),
        ("POST", "/api/posts/{postId}/ai-summary"), ("POST", "/api/reviews/{reviewId}/reply-draft")}
    with TestClient(application_for()) as client:
        schema = client.get("/openapi.json").json()
        actual = {(method.upper(), path) for path, operations in schema["paths"].items() for method in operations}
        assert actual == expected
        assert client.get("/health").json() == {"status": "ok"}
    with TestClient(create_app(Settings(_env_file=None, fake_llm=True))) as client:
        assert len(client.get("/openapi.json").json()["paths"]) == 3


@pytest.mark.parametrize("backend", BACKENDS)
def test_board_storage_and_reads_are_masked_before_any_generation(backend):
    application = application_for(backend)
    with TestClient(application) as client:
        created = client.post("/api/posts", json={"title": "전화 010-0000-0000",
            "authorAlias": "sample@example.invalid", "content": "900101-1234567 상담 자료"})
        assert created.status_code == 201
        post = created.json()
        assert post["title"] == "전화 [PHONE]" and post["authorAlias"] == "[EMAIL]"
        assert post["content"] == "[ID_NUMBER] 상담 자료"
        assert client.get("/api/posts").json() == [post]
        assert client.get(f'/api/posts/{post["postId"]}').json() == post
        response = client.post(f'/api/posts/{post["postId"]}/reviews', json={
            "rating": 5, "content": "sample@example.invalid 연락", "authorAlias": "010-0000-0000"})
        review = response.json()
        assert response.status_code == 201 and review["content"] == "[EMAIL] 연락"
        assert review["authorAlias"] == "[PHONE]" and review["replyDraft"] is None
        assert client.get(f'/api/posts/{post["postId"]}/reviews').json() == [review]
        assert not application.state.budget_store.reservations


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("action", ["summary", "reply"])
def test_entire_generated_output_is_reviewed_masked_and_only_safe_reply_is_saved(backend, action):
    application = application_for(backend)
    provider = SimpleNamespace(model="synthetic", ask=AsyncMock(return_value=
        "감사합니다. 무조건 승소합니다. 연락처 010-0000-0000입니다."))
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        post_id, review_id = seed(client)
        path = f"/api/posts/{post_id}/ai-summary" if action == "summary" else f"/api/reviews/{review_id}/reply-draft"
        response = client.post(path)
        assert response.status_code == 200, response.text
        draft = response.json()
        assert draft["reviewRequired"] and draft["reasonCode"] == "MARKETING_REVIEW_REQUIRED"
        assert draft["matchedRules"] == ["UNCONDITIONAL_WIN"]
        assert "무조건 승소" not in draft["text"] and "[PHONE]" in draft["text"]
        assert draft["status"] == "DRAFT" and draft["ruleVersion"] == marketing_core.RULE_VERSION
        assert not application.state.risk_store.events
        assert application.state.admission.active == 0
        assert all(r.state == "ESTIMATED" for r in application.state.budget_store.reservations.values())
        read = client.get(f"/api/posts/{post_id}/reviews").json()[0]
        assert (read["replyDraft"]["text"] == draft["text"]) if action == "reply" else read["replyDraft"] is None
        payload = json.loads(provider.ask.await_args.args[1])
        assert "authorAlias" not in payload and "author_alias" not in payload


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("rating,word", [(1, "사과"), (2, "사과"), (3, "개선"), (4, "감사"), (5, "감사")])
def test_rating_instruction_and_all_checks_apply_to_every_rating(backend, rating, word):
    application = application_for(backend)
    provider = SimpleNamespace(model="synthetic", ask=AsyncMock(return_value="상담 서비스 의견을 확인하겠습니다."))
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        post_id, review_id = seed(client, rating)
        response = client.post(f"/api/reviews/{review_id}/reply-draft")
        assert response.status_code == 200 and not response.json()["reviewRequired"]
        assert word in provider.ask.await_args.args[0]
        assert json.loads(provider.ask.await_args.args[1])["rating"] == rating
        assert client.get(f"/api/posts/{post_id}/reviews").json()[0]["replyDraft"]["version"] == 1


@pytest.mark.parametrize("rating", [0, 6, True, 1.5])
def test_invalid_rating_is_422(rating):
    with TestClient(application_for()) as client:
        post_id = client.post("/api/posts", json=POST).json()["postId"]
        assert client.post(f"/api/posts/{post_id}/reviews", json={**REVIEW, "rating": rating}).status_code == 422


@pytest.mark.parametrize("backend", BACKENDS)
def test_checker_failure_does_not_return_or_save_unchecked_draft(backend, monkeypatch):
    def failure(text):
        raise RuntimeError("synthetic private unchecked output")
    monkeypatch.setattr(marketing_core, "check_marketing_response", failure)
    application = application_for(backend)
    provider = SimpleNamespace(model="synthetic", ask=AsyncMock(return_value="synthetic private unchecked output"))
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        post_id, review_id = seed(client)
        for path in (f"/api/posts/{post_id}/ai-summary", f"/api/reviews/{review_id}/reply-draft"):
            response = client.post(path)
            assert response.status_code == 503 and "unchecked" not in response.text
        assert client.get(f"/api/posts/{post_id}/reviews").json()[0]["replyDraft"] is None
        assert not application.state.risk_store.events and application.state.admission.active == 0


@pytest.mark.parametrize("backend", BACKENDS)
def test_missing_records_and_budget_block_never_call_provider(backend):
    application = application_for(backend, budget_limit_usd=0)
    provider = SimpleNamespace(model="synthetic", ask=AsyncMock())
    application.dependency_overrides[get_llm_client] = lambda: provider
    with TestClient(application) as client:
        for path in ("/api/posts/999", "/api/posts/999/reviews"):
            assert client.get(path).status_code == 404
        for path in ("/api/posts/999/ai-summary", "/api/reviews/999/reply-draft"):
            assert client.post(path).status_code == 404
        post_id, review_id = seed(client)
        assert client.post(f"/api/posts/{post_id}/ai-summary").json()["reasonCode"] == "COST_LIMIT_BLOCKED"
        assert client.post(f"/api/reviews/{review_id}/reply-draft").json()["reasonCode"] == "COST_LIMIT_BLOCKED"
        provider.ask.assert_not_awaited()
        assert application.state.admission.active == 0 and not application.state.risk_store.events


def test_summary_rejects_snapshot_changed_during_generation():
    application = application_for()
    post_id = None
    async def ask(instructions, prompt):
        application.state.board_store.create_review(post_id, "합성", 3, "추가 후기")
        return "합성 요약"
    application.dependency_overrides[get_llm_client] = lambda: SimpleNamespace(model="synthetic", ask=ask)
    with TestClient(application) as client:
        post_id, _ = seed(client)
        response = client.post(f"/api/posts/{post_id}/ai-summary")
        assert response.status_code == 409 and response.json()["code"] == "MARKETING_SNAPSHOT_CHANGED"
        assert "합성 요약" not in response.text


def test_competing_replies_cannot_overwrite_a_newer_checked_draft():
    async def scenario():
        application = application_for()
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0
        async def ask(instructions, prompt):
            nonlocal calls
            calls += 1
            n = calls
            if calls == 2:
                entered.set()
            await release.wait()
            return f"합성 답변 {n}"
        application.dependency_overrides[get_llm_client] = lambda: SimpleNamespace(model="synthetic", ask=ask)
        async with application.router.lifespan_context(application):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test") as client:
                post_id = (await client.post("/api/posts", json=POST)).json()["postId"]
                review_id = (await client.post(f"/api/posts/{post_id}/reviews", json=REVIEW)).json()["reviewId"]
                tasks = [asyncio.create_task(client.post(f"/api/reviews/{review_id}/reply-draft")) for _ in range(2)]
                try:
                    await asyncio.wait_for(entered.wait(), 3)
                    release.set()
                    results = await asyncio.gather(*tasks)
                    assert sorted(r.status_code for r in results) == [200, 409]
                    success = next(r.json() for r in results if r.status_code == 200)
                    saved = (await client.get(f"/api/posts/{post_id}/reviews")).json()[0]["replyDraft"]
                    assert saved["text"] == success["text"] and saved["version"] == 1
                finally:
                    release.set()
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.run(scenario())
