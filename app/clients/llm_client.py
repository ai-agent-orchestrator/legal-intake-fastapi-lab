import asyncio
from decimal import Decimal
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings
from app.core.exceptions import AiRequestError
from app.security.decisions import SecurityError


class LlmClient(Protocol):
    model: str
    async def ask(self, instructions: str, prompt: str) -> str: ...
    async def close(self) -> None: ...


class GeneratedText(str):
    """Request-local text with optional reported usage cost; never client-global state."""
    def __new__(cls, text: str, cost_usd: Decimal | None = None):
        result = super().__new__(cls, text)
        result.cost_usd = cost_usd
        return result


class FakeLlmClient:
    model = "fake-llm"

    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds

    async def ask(self, instructions: str, prompt: str) -> str:
        await asyncio.sleep(self.delay_seconds)
        return GeneratedText(
            "(가짜 AI 안내) 상담 전에 사건 경위를 날짜순으로 정리하고, "
            "계약서·대화 기록·입금 내역 등 현재 보유한 자료를 준비하세요. "
            "구체적인 다음 절차는 자료를 검토한 전문가와 확인하세요.", Decimal(0)
        )

    async def close(self) -> None:
        pass


class OpenAiLlmClient:
    def reservation_estimate(self, instructions: str, prompt: str) -> Decimal:
        """Conservative byte-based input bound plus configured output-token cap.

        This is a reservation policy, not a provider billing guarantee. The
        service refuses real calls unless BOTH operator prices are configured.
        """
        if self._input_price is None or self._output_price is None:
            raise SecurityError("MODEL_PRICE_NOT_CONFIGURED")
        input_upper_bound = len((instructions + prompt).encode("utf-8")) + 32
        return (Decimal(input_upper_bound) * self._input_price
                + Decimal(self._max_tokens) * self._output_price) / Decimal(1_000_000)

    def __init__(self, settings: Settings):
        key = settings.openai_api_key
        if key is None or not key.get_secret_value().strip():
            raise ValueError("실제 호출 모드에는 OPENAI_API_KEY가 필요합니다.")
        self.model = settings.openai_model
        self._max_tokens = settings.openai_max_output_tokens
        self._input_price = settings.input_usd_per_million_tokens
        self._output_price = settings.output_usd_per_million_tokens
        self._client = AsyncOpenAI(
            api_key=key.get_secret_value(), timeout=settings.openai_timeout_seconds, max_retries=0,
        )

    async def ask(self, instructions: str, prompt: str) -> str:
        try:
            response = await self._client.responses.create(
                model=self.model, instructions=instructions, input=prompt,
                max_output_tokens=self._max_tokens, store=False,
            )
        except OpenAIError as exc:
            raise AiRequestError("OpenAI 호출에 실패했습니다. 설정과 연결 상태를 확인하세요.") from exc
        usage = getattr(response, "usage", None)
        cost = None
        if usage is not None and self._input_price is not None and self._output_price is not None:
            if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
                   for value in (usage.input_tokens, usage.output_tokens)):
                raise AiRequestError("AI 공급자 사용량 형식이 올바르지 않습니다.")
            cost = (Decimal(usage.input_tokens) * self._input_price
                    + Decimal(usage.output_tokens) * self._output_price) / Decimal(1_000_000)
        if not response.output_text or not response.output_text.strip():
            raise AiRequestError("OpenAI가 안내 본문을 반환하지 않았습니다.", cost_usd=cost)
        return GeneratedText(response.output_text, cost)

    async def close(self) -> None:
        await self._client.close()
