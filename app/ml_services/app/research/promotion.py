from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..training.model_registry import ModelRegistry
from ..training.train_model import evaluate_bundle_on_test
from ..training.training_config import TrainingConfig


def _schema(bundle: Path | None) -> str | None:
    if bundle is None or not (bundle / "config.json").exists():
        return None
    return json.loads((bundle / "config.json").read_text(encoding="utf-8")).get("feature_schema_version")


def promote_candidate(version: str, *, allow_schema_migration: bool = False) -> dict:
    config = TrainingConfig.from_env()
    registry = ModelRegistry(config)
    candidate_dir = registry.candidates_dir / version
    registry.validate_candidate_artifacts(version)
    metrics = json.loads((candidate_dir / "metrics.json").read_text(encoding="utf-8"))
    training_report = json.loads((candidate_dir / "training_report.json").read_text(encoding="utf-8"))
    candidate_config = json.loads((candidate_dir / "config.json").read_text(encoding="utf-8"))
    active = registry.active_bundle_dir()
    active_schema = _schema(active)
    candidate_schema = str(candidate_config.get("feature_schema_version"))
    mode = "schema_upgrade" if active_schema and active_schema != candidate_schema else "same_schema"
    champion_metrics = None
    champion_error = None
    if mode == "same_schema" and active is not None:
        holdout_path = candidate_dir / "evaluation_holdout.parquet"
        if holdout_path.exists():
            try:
                champion_metrics = evaluate_bundle_on_test(active, pd.read_parquet(holdout_path))
            except Exception as error:
                champion_error = str(error)
    passed, reasons = registry.promotion_gate(metrics, champion_metrics, training_report)
    if champion_error:
        passed = False
        reasons.append("champion could not be evaluated on research holdout: " + champion_error)
    if mode == "schema_upgrade" and not allow_schema_migration:
        passed = False
        reasons.append("feature schema migration requires explicit --allow-schema-migration")
    registry.write_promotion_decision(
        version,
        passed,
        reasons,
        mode=mode,
        active_schema=active_schema,
        candidate_schema=candidate_schema,
        schema_migration_authorized=(mode == "schema_upgrade" and allow_schema_migration),
    )
    if not passed:
        registry.update_candidate_decision(version, "rejected", reasons)
        return {"passed": False, "reasons": reasons, "mode": mode}
    updated = registry.promote(version)
    return {"passed": True, "reasons": [], "mode": mode, "registry": updated}


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a frozen research candidate through normal gates")
    parser.add_argument("version")
    parser.add_argument("--allow-schema-migration", action="store_true")
    args = parser.parse_args()
    result = promote_candidate(args.version, allow_schema_migration=args.allow_schema_migration)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
