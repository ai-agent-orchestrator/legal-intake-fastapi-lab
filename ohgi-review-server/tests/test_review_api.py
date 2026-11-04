import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx
from openai import APIConnectionError

from app.clients.llm_client import OpenAiLlmClient
from app.core.config import Settings
from app.core.exceptions import AiRequestError
from app.dependencies import get_llm_client
from app.main import create_app
from app.repositories.review_repository import ReviewRepository
from app.routers.review_router import router


def fake_settings() -> Settings:
    return Settings(_env_file=None, fake_llm=True, fake_llm_delay_seconds=0)


BODY = {"customerName": "연습손님", "rating": 5, "content": "설명이 친절했습니다."}


class ReviewApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(fake_settings())
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def register(self):
        response = self.client.post("/api/reviews", json=BODY)
        self.assertEqual(response.status_code, 201)
        return response.json()["reviewId"]

    def test_create_and_lookup_camel_case(self):
        review_id = self.register()
        response = self.client.get(f"/api/reviews/{review_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reviewId": review_id, **BODY})

    def test_rating_validation(self):
        for rating in [0, 6, 1.5, True]:
            with self.subTest(rating=rating):
                response = self.client.post("/api/reviews", json={**BODY, "rating": rating})
                self.assertEqual(response.status_code, 422)

    def test_blank_fields_and_missing_name(self):
        for body in [{**BODY, "customerName": "  "}, {**BODY, "content": ""},
                     {"rating": 5, "content": "연습 리뷰"}]:
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/api/reviews", json=body).status_code, 422)

    def test_missing_review_custom_404(self):
        response = self.client.get("/api/reviews/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "REVIEW_NOT_FOUND")

    def test_missing_reply_does_not_call_llm(self):
        recorder = SimpleNamespace(model="recording-fake", ask=AsyncMock())
        self.app.dependency_overrides[get_llm_client] = lambda: recorder
        response = self.client.post("/api/reviews/999/reply")
        self.assertEqual(response.status_code, 404)
        recorder.ask.assert_not_awaited()

    def test_reply_awaits_llm_with_stored_review(self):
        review_id = self.register()
        recorder = SimpleNamespace(model="recording-fake", ask=AsyncMock(return_value="정중한 답글 초안"))
        self.app.dependency_overrides[get_llm_client] = lambda: recorder
        response = self.client.post(f"/api/reviews/{review_id}/reply")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reviewId": review_id, "reply": "정중한 답글 초안", "model": "recording-fake"})
        recorder.ask.assert_awaited_once()
        instructions, prompt = recorder.ask.await_args.args
        self.assertIn("사장님", instructions)
        self.assertEqual(json.loads(prompt), BODY)

    def test_llm_failure_is_502(self):
        review_id = self.register()
        failure = SimpleNamespace(model="failing-fake", ask=AsyncMock(side_effect=AiRequestError("연습용 연결 실패")))
        self.app.dependency_overrides[get_llm_client] = lambda: failure
        response = self.client.post(f"/api/reviews/{review_id}/reply")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "AI_REQUEST_FAILED")

    def test_required_execution_models_and_swagger(self):
        routes = {f"{method} {r.path}": inspect.iscoroutinefunction(r.endpoint)
                  for r in router.routes if hasattr(r, "methods") for method in r.methods}
        self.assertFalse(routes["POST /api/reviews"])
        self.assertFalse(routes["GET /api/reviews/{review_id}"])
        self.assertTrue(routes["POST /api/reviews/{review_id}/reply"])
        self.assertEqual(self.client.get("/docs").status_code, 200)

    def test_restart_has_no_previous_memory(self):
        self.register()
        with TestClient(create_app(fake_settings())) as restarted:
            self.assertEqual(restarted.get("/api/reviews/1").status_code, 404)


class ClientAndRepositoryTests(unittest.TestCase):
    def test_concurrent_ids_are_unique(self):
        repository = ReviewRepository()
        with ThreadPoolExecutor(max_workers=8) as pool:
            reviews = list(pool.map(lambda i: repository.save(f"연습{i}", 5, "리뷰"), range(50)))
        self.assertEqual({r.review_id for r in reviews}, set(range(1, 51)))

    def test_sdk_error_mapping_without_real_network(self):
        sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(side_effect=APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com/v1/responses")))), close=AsyncMock())
        settings = Settings(_env_file=None, fake_llm=False, openai_api_key="not-a-real-key")
        with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
            client = OpenAiLlmClient(settings)
            with self.assertRaises(AiRequestError) as failure:
                asyncio.run(client.ask("지시", "리뷰"))
            self.assertNotIn("not-a-real-key", str(failure.exception))
            asyncio.run(client.close())
            sdk.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
