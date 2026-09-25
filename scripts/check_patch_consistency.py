from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def require(path: str) -> Path:
    value = ROOT / path
    if not value.exists():
        raise SystemExit(f"missing required patch file: {path}")
    return value


def main() -> int:
    for path in (
        ".env.example",
        "docker-compose.yml",
        "requirements-test.txt",
        "app/proto/ml/v1/ml.proto",
        "app/backend/api/app/config.py",
        "app/backend/api/app/services/model_compatibility.py",
        "app/backend/api/app/services/strategy_selection.py",
        "app/backend/api/app/services/outcome_service.py",
        "app/backend/api/app/storage/database.py",
        "app/ml_services/app/features_builder.py",
        "app/ml_services/app/training/retrain_pipeline.py",
        "app/ml_services/app/training/build_dataset.py",
        "scripts/test_all.py",
        "scripts/research_synthetic.cmd",
        "scripts/research_synthetic.sh",
        "scripts/research_full.cmd",
        "scripts/research_full.sh",
        "scripts/research_results.cmd",
        "scripts/research_results.sh",
        "scripts/research_candidate.cmd",
        "scripts/research_candidate.sh",
        "scripts/research_promote.cmd",
        "scripts/research_promote.sh",
        "app/ml_services/app/research/runner.py",
        "app/ml_services/app/research/synthetic_runner.py",
        "app/ml_services/app/research/fixtures/synthetic_history.csv",
        "APPLY.md",
        "README.md",
        "CURRENT_STATE.md",
        "TEST_REPORT.md",
        "RUNTIME_VALIDATION.md",
        "DOCKER_VALIDATION.md",
        "DATA_AUDIT.md",
        "TARGET_AUDIT.md",
        "LEAKAGE_AUDIT.md",
        "BACKTEST_REPORT.md",
        "MODEL_COMPARISON.md",
        "WALK_FORWARD_REPORT.md",
        "CALIBRATION_REPORT.md",
        "SENSITIVITY_REPORT.json",
        "PROMOTION_REPORT.md",
        "OUTCOME_MONITORING_REPORT.md",
        "RESEARCH_REPORT.md",
        "EXPERIMENT_RESULTS.md",
        "KNOWN_LIMITATIONS.md",
        "VERIFY_AND_REBUILD.ps1",
    ):
        require(path)

    if (ROOT / ".env.example.outcome-additions").exists():
        raise SystemExit("stale .env.example.outcome-additions must not be shipped")

    compose = yaml.safe_load(require("docker-compose.yml").read_text(encoding="utf-8"))
    services = compose.get("services", {})
    for name in ("backend", "ml_service", "ml_trainer"):
        if name not in services:
            raise SystemExit(f"compose service missing: {name}")
    if "backend_data:/app/data" not in services["backend"].get("volumes", []):
        raise SystemExit("backend_data SQLite volume is missing")
    if "backend_data" not in compose.get("volumes", {}):
        raise SystemExit("backend_data named volume declaration is missing")
    if services["ml_service"].get("healthcheck", {}).get("test") != [
        "CMD", "python", "-m", "app.online.healthcheck"
    ]:
        raise SystemExit("ML healthcheck is not application-aware")
    trainer_volumes = services["ml_trainer"].get("volumes", [])
    if "./runtime:/app/runtime" not in trainer_volumes:
        raise SystemExit("research runtime output mount is missing from ml_trainer")
    if services["ml_trainer"].get("environment", {}).get("ML_RESEARCH_ROOT") != "/app/runtime/research":
        raise SystemExit("ML_RESEARCH_ROOT does not point to persisted research runtime")

    pins = {
        "grpcio": "1.81.1",
        "grpcio-tools": "1.81.1",
        "grpcio-health-checking": "1.81.1",
        "protobuf": "6.33.5",
    }
    req_paths = [
        require("app/backend/api/requirements.txt"),
        require("app/ml_services/requirements.txt"),
    ]
    for req in req_paths:
        text = req.read_text(encoding="utf-8")
        for package, version in pins.items():
            if f"{package}=={version}" not in text:
                raise SystemExit(f"{req}: {package} is not pinned to {version}")

    env = require(".env.example").read_text(encoding="utf-8")
    for name in (
        "OUTCOME_TARGET_HORIZON_BARS",
        "OUTCOME_TARGET_HORIZON_MINUTES",
        "OUTCOME_FEE",
        "OUTCOME_SLIPPAGE",
        "OUTCOME_MIN_NET_RETURN",
        "OUTCOME_MAX_DRAWDOWN",
        "OUTCOME_AUTO_EVALUATION",
        "OUTCOME_CHECK_INTERVAL_SECONDS",
        "OUTCOME_BATCH_SIZE",
        "OUTCOME_MAX_RETRIES",
    ):
        if not re.search(rf"(?m)^{re.escape(name)}=", env):
            raise SystemExit(f".env.example is missing {name}")

    proto = require("app/proto/ml/v1/ml.proto").read_text(encoding="utf-8")
    if proto.count("service MLService") != 1:
        raise SystemExit("protobuf source must contain exactly one MLService")

    frontend = require("app/backend/api/app/static/app.js").read_text(encoding="utf-8")
    if "innerHTML" in frontend:
        raise SystemExit("frontend still uses innerHTML")
    if "data.supported_intervals" not in frontend:
        raise SystemExit("frontend does not derive intervals from model-info")

    features = require("app/ml_services/app/features_builder.py").read_text(encoding="utf-8")
    if "latest_strict_inference_row" not in features:
        raise SystemExit("strict online inference row contract is missing")

    pipeline = require("app/ml_services/app/training/retrain_pipeline.py").read_text(encoding="utf-8")
    if "--allow-schema-migration" not in pipeline:
        raise SystemExit("schema migration CLI gate is missing")

    target = require("app/ml_services/app/training/build_dataset.py").read_text(encoding="utf-8")
    if "first_touch_atr_rr" not in target or "stop_loss" not in target:
        raise SystemExit("first-touch target contract is missing")

    print("patch consistency: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
