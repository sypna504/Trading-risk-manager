from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..training.training_config import TrainingConfig


@dataclass(frozen=True, slots=True)
class TargetExperiment:
    name: str
    definition: str = "first_touch_atr_rr"
    horizon_minutes: int = 360
    atr_stop_multiplier: float = 1.5
    reward_ratio: float = 1.5
    minimum_net_return: float = 0.002
    maximum_drawdown: float = -0.015

    def apply(self, base: TrainingConfig) -> TrainingConfig:
        return replace(
            base,
            target_definition=self.definition,
            target_horizon_minutes=self.horizon_minutes,
            target_horizon=max(self.horizon_minutes // 60, 1),
            risk_atr_stop_multiplier=self.atr_stop_multiplier,
            risk_reward_ratio=self.reward_ratio,
            minimum_net_return=self.minimum_net_return,
            maximum_target_drawdown=self.maximum_drawdown,
            deploy_after_training=False,
            candidate_only=True,
            allow_schema_migration=False,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "definition": self.definition,
            "horizon_minutes": self.horizon_minutes,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "reward_ratio": self.reward_ratio,
            "minimum_net_return": self.minimum_net_return,
            "maximum_drawdown": self.maximum_drawdown,
        }


def _default_targets() -> list[TargetExperiment]:
    # Coarse target search. It intentionally samples the requested ATR/R/horizon
    # space instead of blindly evaluating the full Cartesian grid. The final
    # holdout is never used to choose among these configurations.
    return [
        TargetExperiment("ft_atr100_r10_3h", horizon_minutes=180, atr_stop_multiplier=1.00, reward_ratio=1.0),
        TargetExperiment("ft_atr125_r15_6h", horizon_minutes=360, atr_stop_multiplier=1.25, reward_ratio=1.5),
        TargetExperiment("ft_atr150_r20_6h", horizon_minutes=360, atr_stop_multiplier=1.50, reward_ratio=2.0),
        TargetExperiment("ft_atr150_r20_12h", horizon_minutes=720, atr_stop_multiplier=1.50, reward_ratio=2.0),
        TargetExperiment("ft_atr200_r25_12h", horizon_minutes=720, atr_stop_multiplier=2.00, reward_ratio=2.5),
        TargetExperiment("ft_atr200_r30_24h", horizon_minutes=1440, atr_stop_multiplier=2.00, reward_ratio=3.0),
        TargetExperiment(
            "horizon_net_6h",
            definition="horizon_return_drawdown",
            horizon_minutes=360,
            atr_stop_multiplier=1.5,
            reward_ratio=2.0,
            minimum_net_return=0.003,
            maximum_drawdown=-0.02,
        ),
        TargetExperiment(
            "horizon_net_12h",
            definition="horizon_return_drawdown",
            horizon_minutes=720,
            atr_stop_multiplier=1.5,
            reward_ratio=2.0,
            minimum_net_return=0.004,
            maximum_drawdown=-0.025,
        ),
    ]


@dataclass(slots=True)
class ResearchConfig:
    training: TrainingConfig = field(default_factory=TrainingConfig.from_env)
    output_root: Path = field(default_factory=lambda: Path(os.getenv("ML_RESEARCH_ROOT", "runtime/research")))
    mode: str = "full"
    final_holdout_days: int = field(default_factory=lambda: int(os.getenv("ML_RESEARCH_FINAL_HOLDOUT_DAYS", "45")))
    development_min_rows: int = field(default_factory=lambda: int(os.getenv("ML_RESEARCH_DEVELOPMENT_MIN_ROWS", "600")))
    minimum_final_trades: int = field(default_factory=lambda: int(os.getenv("ML_RESEARCH_MIN_FINAL_TRADES", "40")))
    minimum_positive_wf_rate: float = field(default_factory=lambda: float(os.getenv("ML_RESEARCH_MIN_WF_POSITIVE_RATE", "0.60")))
    minimum_oos_profit_factor: float = field(default_factory=lambda: float(os.getenv("ML_RESEARCH_MIN_OOS_PF", "1.05")))
    minimum_oos_portfolio_return: float = 0.0
    require_positive_cost_1_5x: bool = True
    prefer_nonnegative_cost_2x: bool = True
    maximum_symbol_pnl_share: float = 0.55
    maximum_month_pnl_share: float = 0.70
    minimum_positive_seed_rate: float = 0.60
    model_seeds: list[int] = field(default_factory=lambda: [42, 137, 271, 509, 887])
    target_experiments: list[TargetExperiment] = field(default_factory=_default_targets)

    def __post_init__(self) -> None:
        self.mode = self.mode.strip().lower()
        if self.mode not in {"quick", "full"}:
            raise ValueError("research mode must be quick or full")
        if self.training.exchange != "binance":
            raise ValueError("validated research flow currently supports Binance only")
        if self.training.interval != "1h":
            raise ValueError("validated research flow currently supports 1h only")
        if self.final_holdout_days < 14:
            raise ValueError("final holdout must be at least 14 days")
        self.output_root = self.output_root.expanduser().resolve()
        if self.mode == "quick":
            self.target_experiments = self.target_experiments[:3]
            self.model_seeds = self.model_seeds[:2]

    @property
    def model_parameter_space(self) -> list[dict[str, Any]]:
        if self.mode == "quick":
            base = [
                dict(name="d4_lr05", iterations=700, learning_rate=0.05, depth=4, l2_leaf_reg=8.0, random_strength=0.5, bagging_temperature=0.5),
                dict(name="d6_lr03", iterations=1000, learning_rate=0.03, depth=6, l2_leaf_reg=10.0, random_strength=0.8, bagging_temperature=0.8),
            ]
        else:
            base = [
                dict(name="d4_lr04", iterations=1400, learning_rate=0.04, depth=4, l2_leaf_reg=6.0, random_strength=0.4, bagging_temperature=0.4),
                dict(name="d5_lr03", iterations=1800, learning_rate=0.03, depth=5, l2_leaf_reg=8.0, random_strength=0.6, bagging_temperature=0.6),
                dict(name="d6_lr025", iterations=2200, learning_rate=0.025, depth=6, l2_leaf_reg=10.0, random_strength=0.8, bagging_temperature=0.8),
                dict(name="d7_lr02", iterations=2600, learning_rate=0.02, depth=7, l2_leaf_reg=12.0, random_strength=1.0, bagging_temperature=1.0),
            ]
        return base
