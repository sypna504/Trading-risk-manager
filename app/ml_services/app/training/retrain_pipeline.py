from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .build_dataset import build_dataset
from .data_validation import validate_dataset
from .drift_report import build_drift_report
from .model_registry import ModelRegistry, atomic_write_json
from .train_model import evaluate_bundle_on_test, train_candidate
from .training_config import TrainingConfig
from .update_history import update_history
from .window_selection import compare_training_windows


from .pipeline_lock import PipelineLock
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dataset_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_last_run(config: TrainingConfig) -> dict[str, Any]:
    path = config.reports_path / "last_run_state.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _hours_since(value: str | None) -> float | None:
    if not value:
        return None
    timestamp = pd.to_datetime(value, utc=True)
    return float((pd.Timestamp.now(tz="UTC") - timestamp).total_seconds() / 3600)


def _bundle_schema(bundle: Path | None) -> str | None:
    if bundle is None:
        return None
    config_path = bundle / "config.json"
    if not config_path.exists():
        return None
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return str(payload.get("feature_schema_version") or "legacy_v2")


def _history_guard_stats(
    config: TrainingConfig,
    last_training_data_timestamp: str | None,
) -> dict[str, Any]:
    if not config.history_path.exists():
        return {
            "new_unique_timestamps_since_training": 0,
            "expected_symbols": list(config.symbols),
            "available_symbols": [],
            "missing_symbols": list(config.symbols),
            "missing_required_symbols": list(config.required_symbols),
            "symbol_coverage_rate": 0.0,
        }
    history = pd.read_parquet(config.history_path, columns=["timestamp", "symbol"])
    history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True)
    history["symbol"] = history["symbol"].astype(str).str.upper().str.replace("/", "", regex=False).str.replace("-", "", regex=False)
    counts = history.groupby("symbol").size()
    expected = list(dict.fromkeys(config.symbols))
    available = sorted(
        symbol for symbol in expected if int(counts.get(symbol, 0)) >= config.minimum_history_rows
    )
    missing = sorted(set(expected) - set(available))
    missing_required = sorted(set(config.required_symbols) - set(available))
    if last_training_data_timestamp:
        after = history[
            history["timestamp"] > pd.to_datetime(last_training_data_timestamp, utc=True)
        ]
        new_unique = int(after["timestamp"].nunique())
    else:
        new_unique = int(history["timestamp"].nunique())
    return {
        "new_unique_timestamps_since_training": new_unique,
        "expected_symbols": expected,
        "available_symbols": available,
        "missing_symbols": missing,
        "missing_required_symbols": missing_required,
        "symbol_coverage_rate": len(available) / len(expected) if expected else 0.0,
        "rows_per_symbol": {symbol: int(counts.get(symbol, 0)) for symbol in expected},
    }


def _restart_service(config: TrainingConfig) -> None:
    subprocess.run(
        ["docker", "compose", "restart", config.docker_compose_service],
        check=True,
    )


def _verify_inference_version(url: str, expected_version: str) -> dict[str, Any]:
    if not url:
        return {"skipped": True, "reason": "ML_INFERENCE_VERSION_URL is not configured"}
    with urllib.request.urlopen(url, timeout=15) as response:  # nosec B310: configured internal endpoint
        payload = json.loads(response.read().decode("utf-8"))
    actual = payload.get("model_version")
    if actual != expected_version:
        raise RuntimeError(
            f"inference version mismatch: expected={expected_version}, actual={actual}"
        )
    return {"skipped": False, "model_version": actual}


def _write_run_report(config: TrainingConfig, run_id: str, report: dict[str, Any]) -> Path:
    run_directory = config.reports_path / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    report_path = run_directory / "training_report.json"
    atomic_write_json(report, report_path)
    atomic_write_json(report, config.reports_path / "latest_training_report.json")
    return report_path


def run_pipeline(
    mode: str = "manual",
    force: bool = False,
    allow_schema_migration: bool = False,
    config: TrainingConfig | None = None,
) -> dict[str, Any]:
    config = config or TrainingConfig.from_env()
    if force:
        config.force_retrain = True
    if allow_schema_migration:
        config.allow_schema_migration = True
    run_id = _utc_now().strftime("run_%Y%m%d_%H%M%S")
    started = _utc_now()
    report: dict[str, Any] = {
        "run_id": run_id,
        "mode": mode,
        "start_time": started.isoformat(),
        "status": "running",
        "errors": [],
        "promotion": None,
    }
    run_directory = config.reports_path / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"retrain_pipeline.{run_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"
        )
        file_handler = logging.FileHandler(
            run_directory / "pipeline.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    with PipelineLock(config.lock_path):
        try:
            logger.info("starting retrain pipeline mode=%s", mode)
            previous_state = _read_last_run(config)
            history_report = update_history(config)
            report["history_update"] = history_report
            logger.info(
                "history updated: added=%s corrected=%s final_rows=%s",
                history_report.get("added_unique_rows"),
                history_report.get("updated_existing_rows"),
                history_report.get("final_rows"),
            )
            added_rows = int(history_report.get("added_unique_rows", 0))
            updated_rows = int(history_report.get("updated_existing_rows", 0))
            changed_rows = int(history_report.get("changed_rows", added_rows + updated_rows))

            last_training_data_timestamp = previous_state.get(
                "last_training_data_timestamp"
            )
            guard_stats = _history_guard_stats(
                config, last_training_data_timestamp
            )
            new_unique_timestamps = int(
                guard_stats["new_unique_timestamps_since_training"]
            )
            coverage_rate = float(guard_stats["symbol_coverage_rate"])
            missing_required = list(guard_stats["missing_required_symbols"])

            hours_since_training = _hours_since(previous_state.get("last_training_time"))
            report["guards"] = {
                "added_unique_rows": added_rows,
                "updated_existing_rows": updated_rows,
                "changed_rows": changed_rows,
                **guard_stats,
                "hours_since_last_training": hours_since_training,
                "minimum_new_unique_timestamps": config.minimum_new_unique_timestamps,
                "minimum_hours_between_retrains": config.minimum_hours_between_retrains,
                "minimum_symbol_coverage": config.minimum_symbol_coverage,
                "force_retrain": config.force_retrain,
            }

            history_hash = history_report.get("history_hash")
            data_unchanged = bool(
                history_hash
                and history_hash == previous_state.get("last_history_hash")
            )
            report["guards"]["data_unchanged"] = data_unchanged

            should_skip = False
            skip_reasons: list[str] = []
            if not config.force_retrain:
                if config.retrain_on_data_change_only and data_unchanged:
                    should_skip = True
                    skip_reasons.append("history content has not changed")
                if new_unique_timestamps < config.minimum_new_unique_timestamps:
                    should_skip = True
                    skip_reasons.append(
                        "not enough new unique time bars since previous training"
                    )
                if (
                    hours_since_training is not None
                    and hours_since_training < config.minimum_hours_between_retrains
                ):
                    should_skip = True
                    skip_reasons.append("minimum time between retrains has not elapsed")

            if should_skip:
                report.update(
                    {
                        "status": "skipped",
                        "skip_reasons": skip_reasons,
                        "end_time": _utc_now().isoformat(),
                    }
                )
                logger.info("pipeline skipped: %s", ", ".join(skip_reasons))
                report_path = _write_run_report(config, run_id, report)
                report["report_path"] = str(report_path)
                return report

            # Symbol coverage is a hard data-quality gate only when a training
            # run will proceed. --force bypasses scheduling guards, not quality.
            if coverage_rate < config.minimum_symbol_coverage:
                raise ValueError(
                    "history symbol coverage below minimum: "
                    f"coverage={coverage_rate:.3f}, required={config.minimum_symbol_coverage:.3f}, "
                    f"missing={guard_stats['missing_symbols']}"
                )
            if missing_required:
                raise ValueError(
                    "required symbols are missing or have insufficient history: "
                    + ", ".join(missing_required)
                )

            if config.auto_select_training_window:
                history_frame = pd.read_parquet(config.history_path)
                window_report = compare_training_windows(history_frame, config)
                config.training_window_days = int(
                    window_report["selected_training_window_days"]
                )
                report["training_window_selection"] = window_report
            else:
                report["training_window_selection"] = {
                    "selected_training_window_days": config.training_window_days,
                    "selection_reason": "configured default",
                }

            dataset = build_dataset(config=config)
            logger.info("dataset built: rows=%s", len(dataset))
            dataset_validation = validate_dataset(
                dataset,
                minimum_rows=config.minimum_dataset_rows,
                minimum_class_rows=config.minimum_class_rows,
            )
            report["dataset_report"] = dataset.attrs.get("dataset_report", {})
            report["dataset_validation"] = dataset_validation.report
            if not dataset_validation.valid:
                raise ValueError(
                    "dataset validation failed: "
                    + "; ".join(dataset_validation.report["errors"])
                )

            registry = ModelRegistry(config)
            if config.allow_legacy_bootstrap:
                registry.bootstrap_legacy()
            active_bundle = registry.active_bundle_dir()
            candidate = train_candidate(dataset, config=config, registry=registry)
            candidate_metrics = candidate["metrics"]
            logger.info("candidate trained: version=%s", candidate["version"])

            candidate_schema = str(
                candidate["config"].get("feature_schema_version") or "unknown"
            )
            active_schema = _bundle_schema(active_bundle)
            promotion_mode = (
                "schema_upgrade"
                if active_schema is not None and active_schema != candidate_schema
                else "same_schema"
            )
            champion_metrics = None
            champion_evaluation_error = None

            if promotion_mode == "same_schema" and active_bundle is not None:
                try:
                    champion_metrics = evaluate_bundle_on_test(
                        active_bundle,
                        candidate["test_frame"],
                    )
                except Exception as error:
                    champion_evaluation_error = str(error)

            artifact_error = None
            try:
                registry.validate_candidate_artifacts(candidate["version"])
            except Exception as error:
                artifact_error = str(error)

            try:
                passed, reasons = registry.promotion_gate(
                    candidate_metrics,
                    champion_metrics if promotion_mode == "same_schema" else None,
                    candidate["training_report"],
                )
            except TypeError:
                passed, reasons = registry.promotion_gate(
                    candidate_metrics,
                    champion_metrics if promotion_mode == "same_schema" else None,
                )

            if artifact_error is not None:
                passed = False
                reasons.append("candidate artifact validation failed: " + artifact_error)
            if promotion_mode == "same_schema" and champion_evaluation_error is not None:
                passed = False
                reasons.append(
                    "champion could not be evaluated on candidate test: "
                    + champion_evaluation_error
                )
            if promotion_mode == "schema_upgrade" and not config.allow_schema_migration:
                passed = False
                reasons.append(
                    "feature schema migration requires explicit --allow-schema-migration"
                )

            report["candidate"] = {
                "version": candidate["version"],
                "path": str(candidate["candidate_dir"]),
                "metrics": candidate_metrics,
                "training": candidate["training_report"],
            }
            report["champion_metrics"] = champion_metrics
            report["champion_evaluation_error"] = champion_evaluation_error
            if config.candidate_only:
                passed = False
                reasons.append("candidate_only mode is enabled")

            registry.write_promotion_decision(
                candidate["version"],
                passed,
                reasons,
                mode=promotion_mode,
                active_schema=active_schema,
                candidate_schema=candidate_schema,
                schema_migration_authorized=(
                    promotion_mode == "schema_upgrade"
                    and config.allow_schema_migration
                ),
            )
            report["promotion"] = {
                "passed": passed,
                "reasons": reasons,
                "mode": promotion_mode,
                "active_schema": active_schema,
                "candidate_schema": candidate_schema,
                "schema_migration_authorized": (
                    promotion_mode == "schema_upgrade"
                    and config.allow_schema_migration
                ),
            }

            if passed and config.deploy_after_training:
                logger.info("candidate passed promotion gates")
                registry_data = registry.promote(candidate["version"])
                report["promotion"]["registry"] = registry_data
                if config.restart_service_after_promotion:
                    _restart_service(config)
                report["inference_verification"] = _verify_inference_version(
                    config.inference_version_url,
                    candidate["version"],
                )
                active_after = candidate["version"]
            else:
                logger.info("candidate not promoted: %s", ", ".join(reasons))
                decision = "rejected" if not passed else "trained_not_deployed"
                registry.update_candidate_decision(
                    candidate["version"], decision, reasons
                )
                active_after = registry.read().get("active_model_version")

            midpoint = max(len(dataset) // 2, 1)
            drift_report = build_drift_report(
                dataset.iloc[:midpoint],
                dataset.iloc[midpoint:],
                feature_columns=FEATURE_COLUMNS_IMPORT(),
                model_train_end=candidate["config"].get("train_end"),
            )
            report["drift_report"] = drift_report
            report["active_model_after_run"] = active_after
            report["status"] = "completed"
            report["end_time"] = _utc_now().isoformat()
            report["duration_seconds"] = (
                _utc_now() - started
            ).total_seconds()

            report_path = _write_run_report(config, run_id, report)
            logger.info("pipeline completed: active_model=%s", active_after)
            state = {
                "last_run_id": run_id,
                "last_training_time": report["end_time"],
                "last_dataset_hash": _dataset_hash(config.dataset_path),
                "last_history_hash": history_report.get("history_hash"),
                "last_training_data_timestamp": history_report.get(
                    "validation", {}
                ).get("max_timestamp"),
                "active_model_version": active_after,
                "report_path": str(report_path),
            }
            atomic_write_json(state, config.reports_path / "last_run_state.json")
            report["report_path"] = str(report_path)
            return report

        except Exception as error:
            logger.exception("retrain pipeline failed")
            report["status"] = "failed"
            report["errors"].append(str(error))
            report["end_time"] = _utc_now().isoformat()
            report["duration_seconds"] = (_utc_now() - started).total_seconds()
            report_path = _write_run_report(config, run_id, report)
            report["report_path"] = str(report_path)
            raise


def FEATURE_COLUMNS_IMPORT() -> list[str]:
    # local import avoids loading CatBoost before data-update-only guards finish
    from ..features_builder import FEATURE_COLUMNS

    return list(FEATURE_COLUMNS)


def _print_status(config: TrainingConfig) -> None:
    registry = ModelRegistry(config).read()
    latest_report = config.reports_path / "latest_training_report.json"
    print(json.dumps({"registry": registry, "latest_report": str(latest_report)}, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrain and deploy trading risk model")
    parser.add_argument("--mode", choices=["manual", "daily", "hourly"], default="manual")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--allow-schema-migration",
        action="store_true",
        help="explicitly authorize a validated v2->v3 schema upgrade",
    )
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    config = TrainingConfig.from_env()
    try:
        if args.rollback:
            result = ModelRegistry(config).rollback()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.status:
            _print_status(config)
            return 0
        result = run_pipeline(
            mode=args.mode,
            force=args.force,
            allow_schema_migration=args.allow_schema_migration,
            config=config,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as error:
        print(f"retrain pipeline failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
