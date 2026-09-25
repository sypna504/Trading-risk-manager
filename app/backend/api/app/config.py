from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ML_SERVICE_ADDRESS: str = "ml_service:50051"
    ML_SERVICE_PORT: int = Field(default=50051, ge=1, le=65535)
    MIN_CANDLES: int = Field(default=60, ge=60, le=10000)
    DATABASE_PATH: str = "/app/data/trading_risk.db"
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: float = Field(default=15.0, gt=0, le=120)

    MODEL_PATH: str = (
        "/app/app/ml_services/app/models/"
        "risk_model_v2_online.cbm"
    )
    MODEL_CONFIG_PATH: str = (
        "/app/app/ml_services/app/models/"
        "risk_model_v2_online_config.json"
    )
    MODELS_ROOT: str = "/app/app/ml_services/app/models"
    MODEL_REGISTRY_PATH: str = (
        "/app/app/ml_services/app/models/registry.json"
    )
    MODEL_MAX_AGE_DAYS: int = Field(default=30, ge=1, le=3650)
    MODEL_BLOCK_TRADES_WHEN_STALE: bool = False
    MODEL_REQUIRE_VALIDATED_STATUS: bool = False

    ATR_STOP_MULTIPLIER: float = Field(default=1.5, gt=0, le=20)
    MIN_STOP_LOSS_PCT: float = Field(default=0.5, gt=0, le=50)
    RISK_REWARD_RATIO: float = Field(default=2.0, gt=0, le=20)

    # News context is informational only. Disabling it must not change the ML gate.
    NEWS_CONTEXT_ENABLED: bool = True

    # Outcome tracking defaults are only legacy fallbacks. New decisions store
    # the model target contract as an immutable per-decision snapshot.
    OUTCOME_TARGET_HORIZON_BARS: int = Field(default=3, ge=1, le=1000)
    OUTCOME_TARGET_HORIZON_MINUTES: int = Field(default=180, ge=1, le=525600)
    OUTCOME_FEE: float = Field(default=0.001, ge=0, le=0.05)
    OUTCOME_SLIPPAGE: float = Field(default=0.0005, ge=0, le=0.05)
    OUTCOME_MIN_NET_RETURN: float = Field(default=0.002, ge=-1, le=10)
    OUTCOME_MAX_DRAWDOWN: float = Field(default=-0.015, ge=-1, le=0)
    OUTCOME_AUTO_EVALUATION: bool = True
    OUTCOME_CHECK_INTERVAL_SECONDS: int = Field(default=300, ge=10, le=86400)
    OUTCOME_BATCH_SIZE: int = Field(default=100, ge=1, le=5000)
    OUTCOME_MAX_RETRIES: int = Field(default=5, ge=1, le=100)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL must be a standard Python logging level")
        return normalized


settings = Settings()
