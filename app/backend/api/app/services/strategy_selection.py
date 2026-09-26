from __future__ import annotations

from collections.abc import Sequence
from typing import Any


STRATEGY_TIE_PRIORITY = {"breakout": 0, "mean_reversion": 1}


def prediction_margin(prediction: Any) -> float:
    return float(prediction.prob_good_trade) - float(prediction.threshold)


def select_best_prediction(predictions: Sequence[tuple[str, Any]]) -> tuple[str, Any]:
    """Select a model decision without comparing incompatible raw probabilities.

    A strategy that passes its own gate is always preferred over a strategy that
    fails its gate. Within the same allowed/denied group we rank by probability
    margin (p - threshold), then probability, then deterministic strategy order.
    """
    if not predictions:
        raise ValueError("at least one strategy prediction is required")
    allowed = [item for item in predictions if bool(item[1].trade_allowed)]
    candidates = allowed or list(predictions)
    return max(
        candidates,
        key=lambda item: (
            prediction_margin(item[1]),
            float(item[1].prob_good_trade),
            -STRATEGY_TIE_PRIORITY.get(item[0], 100),
        ),
    )
