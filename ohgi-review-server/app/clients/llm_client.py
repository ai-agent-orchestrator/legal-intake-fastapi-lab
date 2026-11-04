import asyncio
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings
from app.core.exceptions import AiRequestError


class LlmClient(Protocol):
    model: str
    async def ask(self, instructions: str, prompt: str) -> str: ...
    async def close(self) -> None: ...


class FakeLlmClient:
    model = "fake-llm"

    def __init__(self, delay_seconds: float):
        self.delay_seconds = delay_seconds

    async def ask(self, instructions: str, prompt: str) -> str:
        await asyncio.sleep(self.delay_seconds)
        return "(가짜 답글 초안) 소중한 의견 감사합니다. 남겨주신 경험을 확인하고 더 나은 서비스를 준비하겠습니다."

    async def close(self) -> None:
        pass


class OpenAiLlmClient:
    def __init__(self, settings: Settings):
        key = settings.openai_api_key
        if key is None or not key.get_secret_value().strip():
            raise ValueError("실제 호출 모드에는 OPENAI_API_KEY가 필요합니다.")
        self.model = settings.openai_model
        self._max_tokens = settings.openai_max_output_tokens
        self._client = AsyncOpenAI(
            api_key=key.get_secret_value(),
            timeout=settings.openai_timeout_seconds, max_retries=0,
        )

    async def ask(self, instructions: str, prompt: str) -> str:
        try:
            response = await self._client.responses.create(
                model=self.model, instructions=instructions, input=prompt,
                max_output_tokens=self._max_tokens, store=False,
            )
        except OpenAIError as exc:
            # SDK의 원문 오류·키·요청 정보를 HTTP 응답에 그대로 넣지 않는다.
            raise AiRequestError("OpenAI 호출에 실패했습니다. 서버 설정과 연결 상태를 확인하세요.") from exc
        text = response.output_text
        if not text or not text.strip():
            raise AiRequestError("OpenAI가 답글 본문을 반환하지 않았습니다.")
        return text

    async def close(self) -> None:
        await self._client.close()
