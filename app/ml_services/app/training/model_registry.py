from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .training_config import TrainingConfig


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def model_version_now() -> str:
    return datetime.now(timezone.utc).strftime("risk_model_%Y%m%d_%H%M%S")


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def registry_relative_path(path: Path, models_root: Path) -> str:
    root = models_root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"artifact is outside models root: {resolved}") from error
    return relative.as_posix()


def normalize_registry_path_value(value: str | Path) -> str:
    normalized = str(value).strip().replace("\\", "/")
    if not normalized:
        raise ValueError("registry path is empty")
    pure_path = PurePosixPath(normalized)
    parts = tuple(part for part in pure_path.parts if part not in ("", "."))
    if pure_path.is_absolute() or not parts:
        raise ValueError(f"registry path must be relative: {value}")
    if ".." in parts:
        raise ValueError(f"registry path traversal is not allowed: {value}")
    if ":" in parts[0]:
        raise ValueError(f"registry path must not contain a drive: {value}")
    return PurePosixPath(*parts).as_posix()


def repair_registry_payload_paths(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    repaired = dict(payload)
    changed = False
    for key in ("active_model_path", "active_config_path"):
        value = repaired.get(key)
        if value:
            normalized = normalize_registry_path_value(value)
            if normalized != value:
                repaired[key] = normalized
                changed = True
    history = []
    for item in repaired.get("candidate_history", []):
        normalized_item = dict(item)
        value = normalized_item.get("path")
        if value:
            normalized = normalize_registry_path_value(value)
            if normalized != value:
                normalized_item["path"] = normalized
                changed = True
        history.append(normalized_item)
    repaired["candidate_history"] = history
    return repaired, changed


class ModelRegistry:
    def __init__(self, config: TrainingConfig | None = None):
        self.config = config or TrainingConfig.from_env()
        self.root = self.config.models_root
        self.active_dir = self.root / "active"
        self.candidates_dir = self.root / "candidates"
        self.archive_dir = self.root / "archive"
        self.reports_dir = self.root / "reports"
        self.registry_path = self.config.registry_path
        for directory in (
            self.active_dir,
            self.candidates_dir,
            self.archive_dir,
            self.reports_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            atomic_write_json(self.empty_registry(), self.registry_path)
        else:
            self.repair_paths()

    @staticmethod
    def empty_registry() -> dict[str, Any]:
        return {
            "active_model_version": None,
            "previous_model_version": None,
            "active_model_path": None,
            "active_config_path": None,
            "promoted_at": None,
            "rollback_available": False,
            "candidate_history": [],
        }

    def repair_paths(self) -> bool:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        repaired, changed = repair_registry_payload_paths(payload)
        if changed:
            atomic_write_json(repaired, self.registry_path)
        return changed

    def bootstrap_legacy(self) -> dict[str, Any] | None:
        registry = self.read()
        if registry.get("active_model_version"):
            return registry
        if not self.config.allow_legacy_bootstrap:
            return None
        legacy_model = self.root / "risk_model_v2_online.cbm"
        legacy_config = self.root / "risk_model_v2_online_config.json"
        if not legacy_model.exists() or not legacy_config.exists():
            return None
        configuration = json.loads(legacy_config.read_text(encoding="utf-8"))
        version = str(configuration.get("model_version") or "risk_model_v2_online")
        target = self.active_dir / version
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_model, target / "model.cbm")
        configuration["model_version"] = version
        configuration["model_checksum"] = file_checksum(target / "model.cbm")
        configuration["validation_status"] = "legacy_unvalidated"
        atomic_write_json(configuration, target / "config.json")
        registry.update(
            {
                "active_model_version": version,
                "previous_model_version": None,
                "active_model_path": registry_relative_path(target / "model.cbm", self.root),
                "active_config_path": registry_relative_path(target / "config.json", self.root),
                "promoted_at": utc_now_iso(),
                "rollback_available": False,
            }
        )
        atomic_write_json(registry, self.registry_path)
        return registry

    def read(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return self.empty_registry()
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        repaired, _ = repair_registry_payload_paths(payload)
        return repaired

    def active_bundle_dir(self) -> Path | None:
        version = self.read().get("active_model_version")
        if not version:
            return None
        path = self.active_dir / version
        return path if path.exists() else None

    def create_candidate_dir(self, version: str) -> Path:
        path = self.candidates_dir / version
        path.mkdir(parents=True, exist_ok=False)
        return path

    def register_candidate(
        self,
        version: str,
        candidate_dir: Path,
        metrics: dict[str, Any],
        decision: str = "trained",
        reasons: list[str] | None = None,
    ) -> None:
        registry = self.read()
        history = registry.setdefault("candidate_history", [])
        history.append(
            {
                "version": version,
                "path": registry_relative_path(candidate_dir, self.root),
                "created_at": utc_now_iso(),
                "decision": decision,
                "reasons": reasons or [],
                "roc_auc": metrics.get("classification", {}).get("roc_auc"),
                "pr_auc": metrics.get("classification", {}).get("pr_auc"),
                "total_net_return": metrics.get("trading", {}).get("total_net_return"),
                "maximum_drawdown": metrics.get("trading", {}).get("maximum_drawdown"),
            }
        )
        registry["candidate_history"] = history[-100:]
        atomic_write_json(registry, self.registry_path)

    def update_candidate_decision(
        self,
        version: str,
        decision: str,
        reasons: list[str] | None = None,
    ) -> None:
        registry = self.read()
        history = registry.setdefault("candidate_history", [])
        updated = False
        for item in reversed(history):
            if item.get("version") == version:
                item["decision"] = decision
                item["reasons"] = reasons or []
                item["decided_at"] = utc_now_iso()
                updated = True
                break
        if not updated:
            history.append(
                {
                    "version": version,
                    "decision": decision,
                    "reasons": reasons or [],
                    "decided_at": utc_now_iso(),
                }
            )
        registry["candidate_history"] = history[-100:]
        atomic_write_json(registry, self.registry_path)

    def promotion_gate(
        self,
        candidate_metrics: dict[str, Any],
        champion_metrics: dict[str, Any] | None,
        training_report: dict[str, Any] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        classification = candidate_metrics.get("classification", {})
        probabilities = candidate_metrics.get("probabilities", {})
        trading = candidate_metrics.get("trading", {})
        training_report = training_report or {}
        walk_forward = training_report.get("walk_forward", {})
        portfolio = training_report.get("portfolio_backtest", {})

        if classification.get("single_class_test"):
            reasons.append("test contains one class")
        roc_auc = classification.get("roc_auc")
        if roc_auc is None or roc_auc <= 0.5:
            reasons.append("ROC AUC is not above 0.5")
        pr_auc = classification.get("pr_auc")
        positive_rate = classification.get("positive_class_rate")
        if pr_auc is None or positive_rate is None or pr_auc <= positive_rate:
            reasons.append("PR AUC does not beat positive class rate")
        if int(probabilities.get("unique_count") or 0) < self.config.minimum_unique_probabilities:
            reasons.append("probabilities have too few unique values")
        if float(probabilities.get("std") or 0.0) < self.config.minimum_probability_std:
            reasons.append("probability std is below minimum")
        if float(probabilities.get("range") or 0.0) < self.config.minimum_probability_range:
            reasons.append("probability range is below minimum")
        if int(trading.get("trades") or 0) < self.config.minimum_selected_trades:
            reasons.append("too few selected trades")
        mean_return = trading.get("mean_net_return")
        if mean_return is None or float(mean_return) <= 0:
            reasons.append("mean net return is not positive")
        total_return = trading.get("total_net_return")
        if total_return is None or float(total_return) <= 0:
            reasons.append("total net return is not positive")
        profit_factor = trading.get("profit_factor")
        if profit_factor is None or float(profit_factor) <= self.config.minimum_profit_factor:
            reasons.append("profit factor is not above minimum")
        maximum_drawdown = trading.get("maximum_drawdown")
        if maximum_drawdown is None or float(maximum_drawdown) < self.config.maximum_allowed_drawdown:
            reasons.append("maximum drawdown exceeds limit")

        if training_report:
            filtered_portfolio = portfolio.get("filtered", {})
            base_portfolio = portfolio.get("all_signal_baseline", {})
            stress_15 = portfolio.get("cost_stress_1_5x", {})
            stress_20 = portfolio.get("cost_stress_2x", {})
            if not filtered_portfolio:
                reasons.append("portfolio-aware backtest is missing")
            else:
                if float(filtered_portfolio.get("portfolio_return") or 0.0) <= 0:
                    reasons.append("portfolio backtest return is not positive")
                pf = filtered_portfolio.get("profit_factor")
                if pf is None or float(pf) <= self.config.minimum_profit_factor:
                    reasons.append("portfolio backtest profit factor is not above minimum")
                if float(stress_15.get("portfolio_return") or 0.0) <= 0:
                    reasons.append("portfolio return is not positive at 1.5x costs")
                if float(stress_20.get("portfolio_return") or 0.0) <= 0:
                    reasons.append("portfolio return is not positive at 2x costs")
                if base_portfolio:
                    improvement = float(filtered_portfolio.get("portfolio_return") or 0.0) - float(
                        base_portfolio.get("portfolio_return") or 0.0
                    )
                    if improvement <= self.config.minimum_portfolio_improvement:
                        reasons.append("ML filter does not improve the all-signal portfolio baseline")

            completed_folds = int(walk_forward.get("completed_folds") or 0)
            positive_fold_rate = walk_forward.get("positive_return_fold_rate")
            if completed_folds < self.config.minimum_completed_walk_forward_folds:
                reasons.append("not enough completed walk-forward folds")
            if positive_fold_rate is None or float(positive_fold_rate) < self.config.minimum_walk_forward_positive_rate:
                reasons.append("walk-forward positive fold rate is below minimum")

        by_symbol = trading.get("by_symbol", {})
        by_strategy = trading.get("by_strategy", {})
        total_trades = max(int(trading.get("trades") or 0), 1)
        if by_symbol:
            share = max(int(item.get("trades", 0)) for item in by_symbol.values()) / total_trades
            if share > self.config.maximum_symbol_trade_share:
                reasons.append("result is concentrated in one symbol")
        if by_strategy:
            share = max(int(item.get("trades", 0)) for item in by_strategy.values()) / total_trades
            if share > self.config.maximum_strategy_trade_share:
                reasons.append("result is concentrated in one strategy")
        by_month = trading.get("by_month", {})
        # Full production promotion always passes training_report and therefore
        # requires temporal/regime robustness evidence. Standalone metric
        # diagnostics can still call the gate without a report.
        if training_report:
            if len(by_month) < self.config.minimum_test_months:
                reasons.append("OOS trading sample spans too few calendar months")
            else:
                month_share = max(int(item.get("trades", 0)) for item in by_month.values()) / total_trades
                if month_share > self.config.maximum_month_trade_share:
                    reasons.append("result is concentrated in one month")
            for key in ("by_trend_regime", "by_volatility_regime"):
                grouped = trading.get(key, {})
                if not grouped:
                    reasons.append(f"{key.replace('by_', '')} robustness breakdown is missing")
                    continue
                regime_share = max(int(item.get("trades", 0)) for item in grouped.values()) / total_trades
                if regime_share > self.config.maximum_regime_trade_share:
                    reasons.append(f"result is concentrated in one {key.replace('by_', '')}")

        sensitivity = training_report.get("sensitivity", {})
        sensitivity_warnings = sensitivity.get("warnings", [])
        if "raw probabilities are effectively constant" in sensitivity_warnings:
            reasons.append("sensitivity report found constant raw probabilities")
        if "numerical sensitivity is effectively zero" in sensitivity_warnings:
            reasons.append("model has no measurable numerical sensitivity")

        if champion_metrics:
            champion_trading = champion_metrics.get("trading", {})
            champion_classification = champion_metrics.get("classification", {})
            champion_total = champion_trading.get("total_net_return")
            if champion_total is not None and total_return is not None:
                tolerance = max(abs(float(champion_total)) * 0.05, 1e-6)
                if float(total_return) < float(champion_total) - tolerance:
                    reasons.append("candidate trading return is worse than champion")
            champion_dd = champion_trading.get("maximum_drawdown")
            if champion_dd is not None and maximum_drawdown is not None:
                if float(maximum_drawdown) < float(champion_dd) - 0.05:
                    reasons.append("candidate drawdown is materially worse than champion")
            champion_brier = champion_classification.get("brier_score")
            candidate_brier = classification.get("brier_score")
            if champion_brier is not None and candidate_brier is not None:
                if float(candidate_brier) > float(champion_brier) * 1.10:
                    reasons.append("candidate calibration is materially worse")
        return not reasons, reasons

    def validate_candidate_artifacts(self, version: str) -> dict[str, Any]:
        candidate = self.candidates_dir / version
        if not candidate.exists():
            raise FileNotFoundError(f"candidate not found: {candidate}")
        for required in (
            "model.cbm",
            "config.json",
            "metrics.json",
            "training_report.json",
            "sensitivity_report.json",
            "dataset_report.json",
        ):
            if not (candidate / required).exists():
                raise FileNotFoundError(f"candidate artifact missing: {required}")
        config = json.loads((candidate / "config.json").read_text(encoding="utf-8"))
        if config.get("feature_schema_version") != "v3":
            raise ValueError("candidate feature schema must be v3")
        if not config.get("supported_intervals"):
            raise ValueError("candidate supported_intervals is empty")
        if not config.get("supported_strategies"):
            raise ValueError("candidate supported_strategies is empty")
        if not config.get("supported_symbols"):
            raise ValueError("candidate supported_symbols is empty")
        if not config.get("supported_exchanges"):
            raise ValueError("candidate supported_exchanges is empty")
        if config.get("allow_unseen_symbols") is not False:
            raise ValueError("candidate must reject unseen symbols")
        if int(config.get("target_horizon_minutes") or 0) <= 0:
            raise ValueError("candidate target_horizon_minutes is invalid")
        if config.get("entry_convention") != "next_bar_open":
            raise ValueError("candidate entry convention is incompatible")
        expected_checksum = config.get("model_checksum")
        if not expected_checksum or file_checksum(candidate / "model.cbm") != expected_checksum:
            raise ValueError("candidate model checksum is invalid")
        return config

    def write_promotion_decision(
        self,
        version: str,
        passed: bool,
        reasons: list[str],
        *,
        mode: str = "same_schema",
        active_schema: str | None = None,
        candidate_schema: str | None = None,
        schema_migration_authorized: bool = False,
    ) -> Path:
        candidate = self.candidates_dir / version
        if not candidate.exists():
            raise FileNotFoundError(f"candidate not found: {candidate}")
        path = candidate / "promotion_decision.json"
        atomic_write_json(
            {
                "version": version,
                "passed": bool(passed),
                "reasons": list(reasons),
                "mode": mode,
                "active_schema": active_schema,
                "candidate_schema": candidate_schema,
                "schema_migration_authorized": bool(schema_migration_authorized),
                "decided_at": utc_now_iso(),
            },
            path,
        )
        return path

    def promote(self, version: str, *, force: bool = False) -> dict[str, Any]:
        candidate = self.candidates_dir / version
        if not candidate.exists():
            raise FileNotFoundError(f"candidate not found: {candidate}")
        # Authorization is checked before artifact validation so an unapproved
        # bundle cannot cross the promotion boundary.
        decision_path = candidate / "promotion_decision.json"
        if not force:
            if not decision_path.exists():
                raise RuntimeError("promotion decision artifact is missing")
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            if decision.get("version") != version or decision.get("passed") is not True:
                raise RuntimeError("candidate did not pass promotion validation")
            if decision.get("mode") == "schema_upgrade" and not decision.get(
                "schema_migration_authorized"
            ):
                raise RuntimeError("schema upgrade promotion was not explicitly authorized")
        self.validate_candidate_artifacts(version)

        registry = self.read()
        previous_version = registry.get("active_model_version")
        previous_path = self.active_dir / previous_version if previous_version else None
        temporary_active = self.active_dir / f".{version}.tmp"
        final_active = self.active_dir / version
        if temporary_active.exists():
            shutil.rmtree(temporary_active)
        if final_active.exists():
            shutil.rmtree(final_active)
        shutil.copytree(candidate, temporary_active)
        os.replace(temporary_active, final_active)
        final_config_path = final_active / "config.json"
        final_config = json.loads(final_config_path.read_text(encoding="utf-8"))
        final_config["model_status"] = "validated"
        final_config["promoted_at"] = utc_now_iso()
        atomic_write_json(final_config, final_config_path)

        rollback_ready = False
        if previous_path and previous_path.exists():
            archive_target = self.archive_dir / previous_version
            archive_temp = self.archive_dir / f".{previous_version}.tmp"
            if archive_temp.exists():
                shutil.rmtree(archive_temp)
            if archive_target.exists():
                shutil.rmtree(archive_target)
            shutil.copytree(previous_path, archive_temp)
            os.replace(archive_temp, archive_target)
            rollback_ready = True

        new_registry = dict(registry)
        new_registry.update(
            {
                "previous_model_version": previous_version,
                "active_model_version": version,
                "active_model_path": registry_relative_path(final_active / "model.cbm", self.root),
                "active_config_path": registry_relative_path(final_active / "config.json", self.root),
                "promoted_at": utc_now_iso(),
                "rollback_available": rollback_ready,
            }
        )
        atomic_write_json(new_registry, self.registry_path)
        if previous_path and previous_path.exists() and previous_path != final_active:
            shutil.rmtree(previous_path)
        self.update_candidate_decision(version, "promoted", [])
        return self.read()

    def rollback(self) -> dict[str, Any]:
        registry = self.read()
        previous = registry.get("previous_model_version")
        current = registry.get("active_model_version")
        if not previous or not current:
            raise RuntimeError("no previous model available for rollback")
        previous_archive = self.archive_dir / previous
        current_active = self.active_dir / current
        if not previous_archive.exists():
            raise FileNotFoundError(f"archived model not found: {previous_archive}")
        rollback_temp = self.active_dir / f".{previous}.rollback.tmp"
        rollback_active = self.active_dir / previous
        if rollback_temp.exists():
            shutil.rmtree(rollback_temp)
        if rollback_active.exists():
            shutil.rmtree(rollback_active)
        shutil.copytree(previous_archive, rollback_temp)
        os.replace(rollback_temp, rollback_active)
        current_archive = self.archive_dir / current
        if current_active.exists():
            if current_archive.exists():
                shutil.rmtree(current_archive)
            current_archive_temp = self.archive_dir / f".{current}.tmp"
            if current_archive_temp.exists():
                shutil.rmtree(current_archive_temp)
            shutil.copytree(current_active, current_archive_temp)
            os.replace(current_archive_temp, current_archive)
        registry.update(
            {
                "active_model_version": previous,
                "previous_model_version": current,
                "active_model_path": registry_relative_path(rollback_active / "model.cbm", self.root),
                "active_config_path": registry_relative_path(rollback_active / "config.json", self.root),
                "promoted_at": utc_now_iso(),
                "rollback_available": True,
            }
        )
        atomic_write_json(registry, self.registry_path)
        if current_active.exists() and current_active != rollback_active:
            shutil.rmtree(current_active)
        return self.read()
