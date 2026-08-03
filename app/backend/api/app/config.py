from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ML_SERVICE_ADDRESS: str = "ml_service:50051"
    ML_SERVICE_PORT: int = 50051
    MIN_CANDLES: int = 60
    DATABASE_PATH: str = "/app/data/trading_risk.db"
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: float = 15.0

    MODEL_PATH: str = (
        "/app/app/ml_services/app/models/"
        "risk_model_v2_online.cbm"
    )
    MODEL_CONFIG_PATH: str = (
        "/app/app/ml_services/app/models/"
        "risk_model_v2_online_config.json"
    )
    MODEL_MAX_AGE_DAYS: int = 30

    ATR_STOP_MULTIPLIER: float = 1.5
    MIN_STOP_LOSS_PCT: float = 0.5
    RISK_REWARD_RATIO: float = 2.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
