from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Show latest research result without changing registry state")
    parser.add_argument("--root", type=Path, default=Path("runtime/research"))
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()

    latest_path = args.root / "LATEST.json"
    if not latest_path.exists():
        print(f"research result not found: {latest_path}")
        return 2
    payload = json.loads(latest_path.read_text(encoding="utf-8"))
    selected = payload.get("selected") or {}
    final_metrics = payload.get("final_metrics") or {}
    classification = final_metrics.get("classification") or {}
    portfolio = final_metrics.get("portfolio") or {}
    base = portfolio.get("cost_1x") or {}
    candidate = payload.get("candidate")
    summary = {
        "status": payload.get("status"),
        "research_result": payload.get("research_result"),
        "experiment_count": payload.get("experiment_count"),
        "promotion_ready": payload.get("promotion_ready"),
        "promotion_reasons": payload.get("promotion_reasons"),
        "target": selected.get("target"),
        "feature_set": selected.get("feature_set"),
        "architecture": selected.get("architecture"),
        "roc_auc": classification.get("roc_auc"),
        "pr_auc": classification.get("pr_auc"),
        "pr_baseline": classification.get("positive_class_rate"),
        "portfolio_return": base.get("portfolio_return"),
        "profit_factor": base.get("profit_factor"),
        "maximum_drawdown": base.get("maximum_drawdown"),
        "candidate_version": (candidate or {}).get("version"),
        "candidate_dir": (candidate or {}).get("candidate_dir"),
        "production_trading_ready": payload.get("production_trading_ready"),
    }
    if args.candidate:
        summary = {
            "promotion_ready": payload.get("promotion_ready"),
            "promotion_reasons": payload.get("promotion_reasons"),
            "candidate": candidate,
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
