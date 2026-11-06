from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )
    fake_llm: bool = True
    fake_llm_delay_seconds: float = Field(default=0.2, ge=0)
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-6-luna"
    openai_timeout_seconds: float = Field(default=30, gt=0)
    openai_max_output_tokens: int = Field(default=600, gt=0)
    guardrail_backend: Literal["local", "nemo"] = "local"
    risk_ttl_seconds: float = Field(default=1800, gt=0)
    risk_max_sessions: int = Field(default=1000, ge=1)
    risk_block_threshold: int = Field(default=3, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
