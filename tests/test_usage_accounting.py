import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.clients.llm_client import OpenAiLlmClient
from app.core.config import Settings
from app.core.exceptions import AiRequestError
from test_paid_call_service import resources, source


def test_real_service_without_prices_never_calls_provider_or_reserves():
    from app.security.decisions import SecurityError
    async def scenario():
        sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock()), close=AsyncMock())
        settings = Settings(_env_file=None, fake_llm=False, openai_api_key="synthetic-not-a-key")
        with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
            provider = OpenAiLlmClient(settings)
            service, admission, budget = resources()
            with pytest.raises(SecurityError, match="MODEL_PRICE_NOT_CONFIGURED"):
                await service.call(source(), provider, "합성 준비")
            sdk.responses.create.assert_not_awaited()
            assert admission.active == 0 and not budget.reservations
            await provider.close()
    asyncio.run(scenario())


def test_configured_price_bound_is_reserved_before_real_sdk_call():
    from app.security.decisions import PolicyBlocked
    async def scenario():
        sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock()), close=AsyncMock())
        settings = Settings(_env_file=None, fake_llm=False, openai_api_key="synthetic-not-a-key",
            input_usd_per_million_tokens="1", output_usd_per_million_tokens="1000000")
        with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
            provider = OpenAiLlmClient(settings)
            service, admission, budget = resources()
            with pytest.raises(PolicyBlocked) as blocked:
                await service.call(source(), provider, "합성 준비")
            assert blocked.value.decision.reason_code == "COST_LIMIT_BLOCKED"
            sdk.responses.create.assert_not_awaited()
            assert admission.active == 0 and not budget.reservations
            await provider.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("bad_tokens", [None, -1, "NaN"])
def test_invalid_usage_is_estimated_without_publishing_provider_details(bad_tokens):
    async def scenario():
        sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(
            output_text="합성 안내", usage=SimpleNamespace(input_tokens=bad_tokens, output_tokens=1)))), close=AsyncMock())
        settings = Settings(_env_file=None, fake_llm=False, openai_api_key="synthetic-not-a-key",
            input_usd_per_million_tokens="1", output_usd_per_million_tokens="2")
        with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
            provider = OpenAiLlmClient(settings)
            service, admission, budget = resources()
            with pytest.raises(AiRequestError):
                await service.call(source(), provider, "합성 준비")
            assert next(iter(budget.reservations.values())).state == "ESTIMATED"
            assert admission.active == 0 and budget.spent > 0
            await provider.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("empty", [False, True])
def test_reported_token_usage_is_charged_even_for_empty_provider_output(empty):
    async def scenario():
        sdk = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(
            output_text=" " if empty else "합성 상담 준비", usage=SimpleNamespace(input_tokens=100, output_tokens=50)))),
            close=AsyncMock())
        settings = Settings(_env_file=None, fake_llm=False, openai_api_key="synthetic-not-a-key",
            input_usd_per_million_tokens="1", output_usd_per_million_tokens="2")
        with patch("app.clients.llm_client.AsyncOpenAI", return_value=sdk):
            provider = OpenAiLlmClient(settings)
            service, admission, budget = resources()
            if empty:
                with pytest.raises(AiRequestError):
                    await service.call(source(), provider, "합성 준비")
            else:
                assert await service.call(source(), provider, "합성 준비") == "합성 상담 준비"
            row = next(iter(budget.reservations.values()))
            assert row.state == "REPORTED" and row.charged == budget.spent == Decimal("0.0002")
            assert admission.active == 0
            await provider.close()
    asyncio.run(scenario())
