from __future__ import annotations

import hashlib
import json
import math
import threading
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.isotonic import IsotonicRegression


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _apply_calibrator(calibrator: Any | None, probability: float) -> float:
    if calibrator is None:
        return probability
    values = np.asarray([probability], dtype=float)
    if isinstance(calibrator, IsotonicRegression):
        return float(calibrator.predict(values)[0])
    return float(calibrator.predict_proba(values.reshape(-1, 1))[0, 1])


def _portable_registry_path(path_value: str | Path) -> Path:
    normalized = str(path_value).strip().replace("\\", "/")
    if not normalized:
        raise ValueError("registry path is empty")

    pure_path = PurePosixPath(normalized)
    parts = tuple(part for part in pure_path.parts if part not in ("", "."))

    if pure_path.is_absolute() or not parts:
        raise ValueError(f"registry path must be relative: {path_value}")
    if ".." in parts:
        raise ValueError(f"registry path traversal is not allowed: {path_value}")
    if ":" in parts[0]:
        raise ValueError(f"registry path must not contain a drive: {path_value}")

    return Path(*parts)


def _resolve_registry_artifact(models_root: Path, path_value: str | Path) -> Path:
    root = models_root.resolve()
    resolved = (root / _portable_registry_path(path_value)).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"registry path points outside models root: {path_value}"
        ) from error

    return resolved


class ModelPredictor:
    def __init__(
        self,
        model_path: str | Path,
        config_path: str | Path,
        registry_path: str | Path | None = None,
        models_root: str | Path | None = None,
    ):
        self.legacy_model_path = Path(model_path)
        self.legacy_config_path = Path(config_path)
        self.registry_path = Path(registry_path) if registry_path else None
        self.models_root = (
            Path(models_root) if models_root else self.legacy_model_path.parent
        )
        self._lock = threading.RLock()
        self.model: CatBoostClassifier | None = None
        self.calibrator: Any | None = None
        self.config: dict[str, Any] = {}
        self.feature_columns: list[str] = []
        self.cat_features: list[str] = []
        self.threshold = 0.5
        self.model_version = "unknown"
        self.model_path = self.legacy_model_path
        self.config_path = self.legacy_config_path
        self.loaded_at: str | None = None
        self._registry_mtime_ns: int | None = None
        self.reload(force=True)

    def _resolve_paths(self) -> tuple[Path, Path, int | None]:
        if self.registry_path and self.registry_path.exists():
            registry = json.loads(
                self.registry_path.read_text(encoding="utf-8")
            )
            active_version = registry.get("active_model_version")
            model_relative = registry.get("active_model_path")
            config_relative = registry.get("active_config_path")

            if active_version and model_relative and config_relative:
                return (
                    _resolve_registry_artifact(
                        self.models_root,
                        model_relative,
                    ),
                    _resolve_registry_artifact(
                        self.models_root,
                        config_relative,
                    ),
                    self.registry_path.stat().st_mtime_ns,
                )

        return self.legacy_model_path, self.legacy_config_path, None

    def reload(self, force: bool = False) -> bool:
        model_path, config_path, registry_mtime = self._resolve_paths()
        if (
            not force
            and model_path == self.model_path
            and config_path == self.config_path
            and registry_mtime == self._registry_mtime_ns
        ):
            return False

        if not model_path.exists():
            if self.model is not None:
                return False
            raise FileNotFoundError(f"model not found: {model_path}")
        if not config_path.exists():
            if self.model is not None:
                return False
            raise FileNotFoundError(f"model config not found: {config_path}")

        configuration = json.loads(config_path.read_text(encoding="utf-8"))
        feature_columns = list(configuration.get("feature_cols", []))
        cat_features = list(configuration.get("cat_features", []))
        if not feature_columns:
            raise ValueError("model config feature_cols is empty")
        if not set(cat_features).issubset(feature_columns):
            raise ValueError("model config cat_features are not a subset of feature_cols")

        threshold = float(configuration["threshold"])
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("model threshold must be finite and between 0 and 1")

        expected_checksum = configuration.get("model_checksum")
        if expected_checksum and _checksum(model_path) != expected_checksum:
            raise ValueError("model checksum does not match config")

        new_model = CatBoostClassifier()
        new_model.load_model(str(model_path))
        new_calibrator = None
        calibrator_name = configuration.get("calibrator")
        if calibrator_name:
            calibrator_path = config_path.parent / calibrator_name
            if not calibrator_path.exists():
                raise FileNotFoundError(
                    f"calibrator not found: {calibrator_path}"
                )
            new_calibrator = joblib.load(calibrator_path)

        with self._lock:
            self.model = new_model
            self.calibrator = new_calibrator
            self.config = configuration
            self.feature_columns = feature_columns
            self.cat_features = cat_features
            self.threshold = threshold
            self.model_version = str(configuration["model_version"])
            self.model_path = model_path
            self.config_path = config_path
            self.loaded_at = datetime.now(timezone.utc).isoformat()
            self._registry_mtime_ns = registry_mtime

        print(
            "loaded active model: "
            f"version={self.model_version}, "
            f"path={self.model_path}, "
            f"threshold={self.threshold}, "
            f"train_end={self.config.get('train_end')}, "
            f"loaded_at={self.loaded_at}",
            flush=True,
        )
        return True

    def maybe_reload(self) -> None:
        try:
            self.reload(force=False)
        except Exception as error:
            if self.model is None:
                raise
            print(
                f"model reload rejected, keeping current model: {error}",
                flush=True,
            )

    def predict(self, features: pd.DataFrame) -> dict[str, Any]:
        self.maybe_reload()
        with self._lock:
            model = self.model
            calibrator = self.calibrator
            feature_columns = list(self.feature_columns)
            cat_features = list(self.cat_features)
            threshold = self.threshold
            model_version = self.model_version

        if model is None:
            raise RuntimeError("model is not loaded")

        missing_features = [
            column
            for column in feature_columns
            if column not in features.columns
        ]
        if missing_features:
            raise ValueError(f"missing model features: {missing_features}")

        model_features = features[feature_columns].copy()
        for column in cat_features:
            model_features[column] = model_features[column].astype(str)

        numeric_columns = [
            column
            for column in feature_columns
            if column not in cat_features
        ]
        numeric_values = model_features[numeric_columns].apply(
            pd.to_numeric,
            errors="coerce",
        )
        numeric_array = numeric_values.to_numpy(dtype=float)
        if np.isnan(numeric_array).any() or np.isinf(numeric_array).any():
            raise ValueError("inference features contain NaN or inf values")

        raw_probability = float(
            model.predict_proba(
                Pool(data=model_features, cat_features=cat_features)
            )[0, 1]
        )
        probability = _apply_calibrator(calibrator, raw_probability)
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("model returned an invalid probability")

        risk_score = 1.0 - probability
        trade_allowed = probability >= threshold

        if probability >= max(0.65, threshold + 0.10):
            risk_level = "low"
        elif trade_allowed:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "prob_good_trade": probability,
            "raw_prob_good_trade": raw_probability,
            "risk_score": risk_score,
            "trade_allowed": trade_allowed,
            "threshold": threshold,
            "risk_level": risk_level,
            "model_version": model_version,
        }

    def metadata(self) -> dict[str, Any]:
        with self._lock:
            return {
                "model_version": self.model_version,
                "model_path": str(self.model_path),
                "config_path": str(self.config_path),
                "threshold": self.threshold,
                "train_start": self.config.get("train_start"),
                "train_end": self.config.get("train_end"),
                "loaded_at": self.loaded_at,
            }
