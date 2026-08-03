from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _env_int_list(name: str, default: list[int]) -> list[int]:
    value = os.getenv(name)
    if not value:
        return list(default)
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return list(default)
    return [item.strip().upper() for item in value.split(",") if item.strip()]


DEFAULT_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "USDCUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "TRXUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "TONUSDT",
    "SHIBUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "UNIUSDT",
    "ICPUSDT",
    "NEARUSDT",
    "APTUSDT",
    "FILUSDT",
    "XLMUSDT",
    "OPUSDT",
    "SUIUSDT",
    "ATOMUSDT",
    "AAVEUSDT",
    "ALGOUSDT",
    "FETUSDT",
    "VETUSDT",
    "EGLDUSDT",
    "GALAUSDT",
    "SANDUSDT",
    "MANAUSDT",
    "PEPEUSDT",
    "CHZUSDT",
    "FLOWUSDT",
    "GRTUSDT",
    "IMXUSDT",
    "LDOUSDT",
    "MINAUSDT",
    "QNTUSDT",
    "RENDERUSDT",
    "STXUSDT",
    "THETAUSDT",
    "TIAUSDT",
]



@dataclass(slots=True)
class TrainingConfig:
    app_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1]
    )

    exchange: str = "binance"
    symbols: list[str] = field(default_factory=lambda: list(DEFAULT_SYMBOLS))
    interval: str = "1h"
    request_limit: int = 1000
    request_timeout: int = 20
    minimum_history_rows: int = 500
    history_symbol_policy: str = "extend"

    training_window_days: int = 180
    training_window_candidates: list[int] = field(
        default_factory=lambda: [90, 180, 365]
    )
    auto_select_training_window: bool = False
    target_horizon: int = 3
    fee: float = 0.001
    slippage: float = 0.0005

    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    purge_bars: int = 3
    walk_forward_folds: int = 4
    minimum_fold_rows: int = 200

    minimum_dataset_rows: int = 1000
    minimum_class_rows: int = 100
    minimum_selected_trades: int = 50
    minimum_unique_probabilities: int = 20
    maximum_allowed_drawdown: float = -0.35

    minimum_new_candles: int = 24
    minimum_hours_between_retrains: int = 20
    force_retrain: bool = False
    retrain_on_data_change_only: bool = True

    threshold_min: float = 0.30
    threshold_max: float = 0.75
    threshold_step: float = 0.01
    minimum_selected_rate: float = 0.03
    maximum_selected_rate: float = 0.80

    random_seed: int = 42
    early_stopping_rounds: int = 50
    enable_calibration: bool = True
    calibration_method: str = "platt"

    deploy_after_training: bool = True
    restart_service_after_promotion: bool = False
    docker_compose_service: str = "ml_service"
    inference_version_url: str = ""

    history_path: Path | None = None
    dataset_path: Path | None = None
    models_root: Path | None = None
    reports_path: Path | None = None
    registry_path: Path | None = None
    lock_path: Path | None = None

    def __post_init__(self) -> None:
        training_dir = self.app_dir / "training"
        data_dir = training_dir / "data"
        models_dir = self.app_dir / "models"

        self.history_path = self.history_path or data_dir / "history_data.parquet"
        self.dataset_path = self.dataset_path or data_dir / "ml_dataset_v2.parquet"
        self.models_root = self.models_root or models_dir
        self.reports_path = self.reports_path or models_dir / "reports"
        self.registry_path = self.registry_path or models_dir / "registry.json"
        self.lock_path = self.lock_path or training_dir / ".retrain.lock"

        total_ratio = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(total_ratio - 1.0) > 1e-8:
            raise ValueError("train/validation/test ratios must sum to 1")
        if self.target_horizon < 1:
            raise ValueError("target_horizon must be positive")
        if self.purge_bars < self.target_horizon:
            self.purge_bars = self.target_horizon
        if not self.symbols:
            raise ValueError("at least one symbol is required")
        self.symbols = list(dict.fromkeys(symbol.upper().replace("/", "").replace("-", "") for symbol in self.symbols))
        if self.history_symbol_policy not in {"error", "extend", "filter"}:
            raise ValueError("history_symbol_policy must be one of: error, extend, filter")

    @classmethod
    def from_env(cls) -> "TrainingConfig":
        config = cls(
            exchange=os.getenv("ML_EXCHANGE", "binance").lower(),
            symbols=_env_list("ML_SYMBOLS", DEFAULT_SYMBOLS),
            interval=os.getenv("ML_INTERVAL", "1h"),
            request_limit=_env_int("ML_REQUEST_LIMIT", 1000),
            request_timeout=_env_int("ML_REQUEST_TIMEOUT", 20),
            minimum_history_rows=_env_int("ML_MINIMUM_HISTORY_ROWS", 500),
            history_symbol_policy=os.getenv("ML_HISTORY_SYMBOL_POLICY", "extend").strip().lower(),
            training_window_days=_env_int("TRAINING_WINDOW_DAYS", 180),
            training_window_candidates=_env_int_list(
                "ML_TRAINING_WINDOW_CANDIDATES", [90, 180, 365]
            ),
            auto_select_training_window=_env_bool(
                "ML_AUTO_SELECT_TRAINING_WINDOW", False
            ),
            target_horizon=_env_int("ML_TARGET_HORIZON", 3),
            fee=_env_float("ML_FEE", 0.001),
            slippage=_env_float("ML_SLIPPAGE", 0.0005),
            train_ratio=_env_float("ML_TRAIN_RATIO", 0.70),
            validation_ratio=_env_float("ML_VALIDATION_RATIO", 0.15),
            test_ratio=_env_float("ML_TEST_RATIO", 0.15),
            purge_bars=_env_int("ML_PURGE_BARS", 3),
            walk_forward_folds=_env_int("ML_WALK_FORWARD_FOLDS", 4),
            minimum_fold_rows=_env_int("ML_MINIMUM_FOLD_ROWS", 200),
            minimum_dataset_rows=_env_int("ML_MINIMUM_DATASET_ROWS", 1000),
            minimum_class_rows=_env_int("ML_MINIMUM_CLASS_ROWS", 100),
            minimum_selected_trades=_env_int("ML_MINIMUM_SELECTED_TRADES", 50),
            minimum_unique_probabilities=_env_int(
                "ML_MINIMUM_UNIQUE_PROBABILITIES", 20
            ),
            maximum_allowed_drawdown=_env_float(
                "ML_MAXIMUM_ALLOWED_DRAWDOWN", -0.35
            ),
            minimum_new_candles=_env_int("MIN_NEW_CANDLES_FOR_RETRAIN", 24),
            minimum_hours_between_retrains=_env_int(
                "MIN_HOURS_BETWEEN_RETRAINS", 20
            ),
            force_retrain=_env_bool("FORCE_RETRAIN", False),
            retrain_on_data_change_only=_env_bool(
                "RETRAIN_ON_DATA_CHANGE_ONLY", True
            ),
            threshold_min=_env_float("ML_THRESHOLD_MIN", 0.30),
            threshold_max=_env_float("ML_THRESHOLD_MAX", 0.75),
            threshold_step=_env_float("ML_THRESHOLD_STEP", 0.01),
            minimum_selected_rate=_env_float("ML_MINIMUM_SELECTED_RATE", 0.03),
            maximum_selected_rate=_env_float("ML_MAXIMUM_SELECTED_RATE", 0.80),
            random_seed=_env_int("ML_RANDOM_SEED", 42),
            early_stopping_rounds=_env_int("ML_EARLY_STOPPING_ROUNDS", 50),
            enable_calibration=_env_bool("ML_ENABLE_CALIBRATION", True),
            calibration_method=os.getenv("ML_CALIBRATION_METHOD", "platt"),
            deploy_after_training=_env_bool("ML_DEPLOY_AFTER_TRAINING", True),
            restart_service_after_promotion=_env_bool(
                "ML_RESTART_SERVICE_AFTER_PROMOTION", False
            ),
            docker_compose_service=os.getenv("ML_DOCKER_SERVICE", "ml_service"),
            inference_version_url=os.getenv("ML_INFERENCE_VERSION_URL", ""),
        )

        path_mapping = {
            "ML_HISTORY_PATH": "history_path",
            "ML_DATASET_PATH": "dataset_path",
            "ML_MODELS_ROOT": "models_root",
            "ML_REPORTS_PATH": "reports_path",
            "ML_REGISTRY_PATH": "registry_path",
            "ML_LOCK_PATH": "lock_path",
        }
        for env_name, field_name in path_mapping.items():
            value = os.getenv(env_name)
            if value:
                setattr(config, field_name, Path(value).expanduser().resolve())
        config.__post_init__()
        return config

    @property
    def model_search_space(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catboost_current",
                "iterations": 500,
                "learning_rate": 0.04,
                "depth": 5,
                "l2_leaf_reg": 3.0,
                "random_strength": 1.0,
                "bagging_temperature": 1.0,
                "border_count": 128,
            },
            {
                "name": "catboost_regularized",
                "iterations": 700,
                "learning_rate": 0.025,
                "depth": 4,
                "l2_leaf_reg": 10.0,
                "random_strength": 0.5,
                "bagging_temperature": 0.5,
                "border_count": 128,
            },
            {
                "name": "catboost_shallow",
                "iterations": 900,
                "learning_rate": 0.02,
                "depth": 3,
                "l2_leaf_reg": 15.0,
                "random_strength": 0.3,
                "bagging_temperature": 1.0,
                "border_count": 64,
            },
        ]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key, value in list(result.items()):
            if isinstance(value, Path):
                result[key] = str(value)
        return result
