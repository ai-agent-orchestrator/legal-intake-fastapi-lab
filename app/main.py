from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.clients.llm_client import FakeLlmClient, OpenAiLlmClient
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.repositories.intake_repository import IntakeRepository
from app.routers.intake_router import router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config = settings if settings is not None else get_settings()
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
