from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS_ROOT = APP_DIR / "models"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ML_SERVICE_PORT: int = 50051
    MODEL_VERSION: str = "legacy"
    MIN_CANDLES: int = 60

    MODELS_ROOT: Path = Field(
        default=DEFAULT_MODELS_ROOT,
        validation_alias=AliasChoices("ML_MODELS_ROOT", "MODELS_ROOT"),
    )
    MODEL_REGISTRY_PATH: Path = Field(
        default=DEFAULT_MODELS_ROOT / "registry.json",
        validation_alias=AliasChoices(
            "ML_REGISTRY_PATH",
            "MODEL_REGISTRY_PATH",
        ),
    )

    MODEL_PATH: Path = Field(
        default=DEFAULT_MODELS_ROOT / "risk_model_v2_online.cbm",
        validation_alias=AliasChoices("MODEL_PATH", "ML_MODEL_PATH"),
    )
    MODEL_CONFIG_PATH: Path = Field(
        default=DEFAULT_MODELS_ROOT / "risk_model_v2_online_config.json",
        validation_alias=AliasChoices(
            "MODEL_CONFIG_PATH",
            "ML_MODEL_CONFIG_PATH",
        ),
    )


settings = Settings()
