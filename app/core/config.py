from decimal import Decimal
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.compression.economics import ModelPricing


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://gateway:gateway@localhost:5432/gateway"
    redis_url: str = "redis://localhost:6379/0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    dependency_timeout_seconds: float = Field(default=2.0, gt=0, le=30)

    openai_api_key: SecretStr = SecretStr("")

    pricing: dict[str, ModelPricing] = Field(default_factory=dict)
    local_compute_cost_per_second: Decimal = Field(default=Decimal(0), ge=0)

    max_payload_bytes: int = Field(default=1048576, ge=1024, le=10485760)
    trace_console_export: bool = False

    semantic_enabled: bool = False

    @model_validator(mode="after")
    def reject_unimplemented_semantic(self) -> "Settings":
        if self.semantic_enabled:
            raise ValueError("Semantic compression is not implemented; keep it disabled")
        return self
