from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.clients.llm_client import FakeLlmClient, OpenAiLlmClient
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.repositories.intake_repository import IntakeRepository
from app.routers.intake_router import router
from app.security.risk_store import RiskStore
from app.security.session_actions import SessionRiskActions
from app.security.session_guard import ContextSessionGuard
from app.security.nemo_adapter import NemoAdapter


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config = settings if settings is not None else get_settings()
        risk = RiskStore(config.risk_ttl_seconds, config.risk_max_sessions, config.risk_block_threshold)
        adapter = NemoAdapter(SessionRiskActions(risk).registry(), config.guardrail_backend)
        application.state.risk_store = risk
        application.state.session_guard = ContextSessionGuard(adapter)
        application.state.intake_repository = IntakeRepository()
        client = FakeLlmClient(config.fake_llm_delay_seconds) if config.fake_llm else OpenAiLlmClient(config)
        application.state.llm_client = client
        logging.getLogger("uvicorn.error").info(
            "[lifespan] mode=%s model=%s", "fake" if config.fake_llm else "real", client.model,
        )
        try:
            yield
        finally:
            await client.close()

    application = FastAPI(title="Legal Intake · 동기 접수와 비동기 AI 안내", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(application)
    application.include_router(router)
    return application


app = create_app()
