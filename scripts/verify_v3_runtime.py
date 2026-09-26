from __future__ import annotations

import json

from app.features_builder import CAT_FEATURES, FEATURE_COLUMNS, FEATURE_SCHEMA_VERSION
from app.training.training_config import TrainingConfig


def main() -> None:
    config = TrainingConfig.from_env()
    errors: list[str] = []

    if FEATURE_SCHEMA_VERSION != "v3":
        errors.append(f"FEATURE_SCHEMA_VERSION={FEATURE_SCHEMA_VERSION!r}, expected 'v3'")
    if "interval" not in FEATURE_COLUMNS:
        errors.append("interval is missing from FEATURE_COLUMNS")
    if "interval" not in CAT_FEATURES:
        errors.append("interval is missing from CAT_FEATURES")
    for forbidden in ("hour", "weekday"):
        if forbidden in FEATURE_COLUMNS:
            errors.append(f"legacy feature is still enabled: {forbidden}")
    if config.supported_intervals != ["1h"]:
        errors.append(
            f"supported_intervals={config.supported_intervals!r}, expected ['1h']"
        )
    if config.target_horizon_minutes != 180:
        errors.append(
            f"target_horizon_minutes={config.target_horizon_minutes}, expected 180"
        )
    if config.feature_schema_version != "v3":
        errors.append(
            f"config feature_schema_version={config.feature_schema_version!r}, expected 'v3'"
        )

    payload = {
        "ok": not errors,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_count": len(FEATURE_COLUMNS),
        "feature_columns": FEATURE_COLUMNS,
        "cat_features": CAT_FEATURES,
        "supported_intervals": config.supported_intervals,
        "target_horizon_minutes": config.target_horizon_minutes,
        "dataset_path": str(config.dataset_path),
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
