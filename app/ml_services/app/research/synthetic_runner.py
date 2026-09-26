from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ..training.training_config import TrainingConfig
from .config import ResearchConfig
from .runner import run_research


class SyntheticResearchConfig(ResearchConfig):
    """Fast deterministic validation profile; full real-data research is unchanged."""

    @property
    def model_parameter_space(self) -> list[dict[str, Any]]:
        return [
            dict(name="synthetic_d4", iterations=60, learning_rate=0.08, depth=4, l2_leaf_reg=6.0, random_strength=0.4, bagging_temperature=0.4),
            dict(name="synthetic_d5", iterations=80, learning_rate=0.06, depth=5, l2_leaf_reg=8.0, random_strength=0.6, bagging_temperature=0.6),
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen research pipeline on a deterministic synthetic OHLCV fixture")
    parser.add_argument("--output-root", type=Path, default=Path("/app/runtime/synthetic_research"))
    args = parser.parse_args()

    fixture = Path(__file__).resolve().parent / "fixtures" / "synthetic_history.csv"
    if not fixture.exists():
        raise FileNotFoundError(f"synthetic fixture not found: {fixture}")

    output = args.output_root.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(fixture)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    # A shorter deterministic window keeps this a smoke/integration validation,
    # not a claim about the economics of the full research process.
    cutoff = frame["timestamp"].min() + pd.Timedelta(days=60)
    frame = frame[frame["timestamp"] < cutoff].copy()
    synthetic_history = output / "synthetic_history.csv"
    frame.to_csv(synthetic_history, index=False)

    training = TrainingConfig.from_env()
    training.history_path = synthetic_history
    training.symbols = sorted(frame["symbol"].astype(str).unique().tolist())
    training.required_symbols = list(training.symbols)
    training.deploy_after_training = False
    training.candidate_only = True
    training.allow_schema_migration = False
    training.walk_forward_folds = 2
    training.bootstrap_iterations = min(training.bootstrap_iterations, 5)
    training.early_stopping_rounds = min(training.early_stopping_rounds, 30)

    research = SyntheticResearchConfig(training=training, mode="quick", output_root=output)
    research.target_experiments = research.target_experiments[:1]
    research.model_seeds = [42]
    research.final_holdout_days = 20
    research.development_min_rows = min(research.development_min_rows, 140)
    research.minimum_final_trades = max(research.minimum_final_trades, 10_000)
    result = run_research(research, update_data=False)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if result.get("status") != "completed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
