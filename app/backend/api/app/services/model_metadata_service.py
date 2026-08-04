from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from ..config import settings


def _safe_relative_path(value: str | Path) -> Path:
    normalized = str(value).strip().replace("\\", "/")
    if not normalized:
        raise ValueError("registry artifact path is empty")
    pure = PurePosixPath(normalized)
    parts = tuple(part for part in pure.parts if part not in ("", "."))
    if pure.is_absolute() or not parts or ".." in parts or ":" in parts[0]:
        raise ValueError(f"unsafe registry artifact path: {value}")
    return Path(*parts)


def _resolve_inside_root(root: Path, value: str | Path) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / _safe_relative_path(value)).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"registry artifact is outside models root: {value}") from error
    return resolved


def resolve_model_artifacts() -> tuple[Path, Path, str | None]:
    models_root = Path(settings.MODELS_ROOT)
    registry_path = Path(settings.MODEL_REGISTRY_PATH)

    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        version = registry.get("active_model_version")
        model_value = registry.get("active_model_path")
        config_value = registry.get("active_config_path")
        if version and model_value and config_value:
            return (
                _resolve_inside_root(models_root, model_value),
                _resolve_inside_root(models_root, config_value),
                str(version),
            )

    return Path(settings.MODEL_PATH), Path(settings.MODEL_CONFIG_PATH), None


def read_active_model_metadata() -> dict[str, Any]:
    model_path, config_path, registry_version = resolve_model_artifacts()
    if not config_path.exists():
        return {
            "model_path": model_path,
            "config_path": config_path,
            "model_file_exists": model_path.exists(),
            "config_file_exists": False,
            "model_version": registry_version,
            "config": {},
        }

    config = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "model_path": model_path,
        "config_path": config_path,
        "model_file_exists": model_path.exists(),
        "config_file_exists": True,
        "model_version": config.get("model_version") or registry_version,
        "config": config,
    }
