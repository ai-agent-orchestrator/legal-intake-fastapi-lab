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
from app.security.policy_actions import policy_registry
from app.security.marketing_actions import marketing_registry
from app.security.resource_actions import ResourceActions
from app.security.admission import AdmissionManager
from app.security.budget_store import BudgetStore
from app.services.paid_call_service import PaidCallService
from app.marketing.board_core import BoardStore


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config = settings if settings is not None else get_settings()
        risk = RiskStore(config.risk_ttl_seconds, config.risk_max_sessions, config.risk_block_threshold)
        admission = AdmissionManager(config.generation_concurrent, config.generation_waiters,
                                     config.generation_wait_seconds)
        budget = BudgetStore(config.budget_limit_usd)
        adapter = NemoAdapter({**SessionRiskActions(risk).registry(), **policy_registry(), **marketing_registry(),
                               **ResourceActions(admission, budget).registry()}, config.guardrail_backend)
        application.state.admission = admission
        application.state.budget_store = budget
        application.state.paid_calls = PaidCallService(adapter, admission, budget,
            config.generation_reservation_usd, config.generation_timeout_seconds)
        application.state.risk_store = risk
        application.state.session_guard = ContextSessionGuard(adapter)
        application.state.intake_repository = IntakeRepository()
        application.state.board_store = BoardStore()
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


def create_full_app(settings: Settings | None = None) -> FastAPI:
    """Serving assembly: 11 operations. create_app remains the three-operation MVP."""
    from app.routers.marketing_router import router as marketing_router
    application = create_app(settings)
    application.include_router(marketing_router)

    @application.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    return application


app = create_full_app()
