from functools import lru_cache
from pathlib import Path
from decimal import Decimal
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )
    fake_llm: bool = True
    rag_enabled: bool = False  # Reserved; no RAG wiring in the synthetic-only v1 scope.
    fake_llm_delay_seconds: float = Field(default=0.2, ge=0)
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-6-luna"
    openai_timeout_seconds: float = Field(default=30, gt=0)
    openai_max_output_tokens: int = Field(default=600, gt=0)
    guardrail_backend: Literal["local", "nemo"] = "local"
    risk_ttl_seconds: float = Field(default=1800, gt=0)
    risk_max_sessions: int = Field(default=1000, ge=1)
    risk_block_threshold: int = Field(default=3, ge=1)
    generation_concurrent: int = Field(default=2, ge=1)
    generation_waiters: int = Field(default=4, ge=0)
    generation_wait_seconds: float = Field(default=0.5, gt=0, allow_inf_nan=False)
    generation_timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)
    budget_limit_usd: Decimal = Field(default=Decimal("1.00"), ge=0, allow_inf_nan=False)
    generation_reservation_usd: Decimal = Field(default=Decimal("0.01"), gt=0, allow_inf_nan=False)
    # Operator-configured prices; no price or billing accuracy is inferred.
    input_usd_per_million_tokens: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_usd_per_million_tokens: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
