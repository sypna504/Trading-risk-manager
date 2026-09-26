from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NEWS_FEATURE_COLUMNS = [
    "news_count_1h",
    "news_count_3h",
    "news_count_6h",
    "news_count_12h",
    "news_count_24h",
    "weighted_sentiment_1h",
    "weighted_sentiment_3h",
    "weighted_sentiment_12h",
    "positive_shock_score",
    "negative_shock_score",
    "geopolitical_risk_score",
    "regulatory_risk_score",
    "macro_risk_score",
    "exchange_risk_score",
    "high_impact_event_count",
    "independent_source_count",
    "novelty_score",
    "news_disagreement",
    "btc_news_score",
    "eth_news_score",
    "asset_specific_news_score",
    "time_since_high_impact_event",
    "scheduled_macro_event_nearby",
]

SENTIMENT_VALUE = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}
DIRECTION_RISK = {"bearish": 1.0, "uncertain": 0.65, "bullish": 0.2}
BROAD_EVENTS = {"regulation", "macro", "geopolitical", "exchange", "stablecoin"}
WINDOWS = (1, 3, 6, 12, 24)


@dataclass(frozen=True, slots=True)
class ResearchSplit:
    train_end: pd.Timestamp
    meta_end: pd.Timestamp
    selection_end: pd.Timestamp
    final_start: pd.Timestamp


@dataclass(slots=True)
class FittedModel:
    name: str
    features: list[str]
    model: Any
    preprocessor: Any | None = None

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        values = _prepare_x(frame, self.features)
        if self.preprocessor is not None:
            values = np.asarray(self.preprocessor.transform(values))
        return np.asarray(self.model.predict_proba(values)[:, 1], dtype=float)


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _asset(symbol: str) -> str:
    normalized = str(symbol).upper().replace("/", "").replace("-", "").strip()
    for quote in ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)]
    return normalized


def _assets(value: Any) -> set[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return set()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return set()
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = [part.strip() for part in text.split(",")]
        value = parsed
    if isinstance(value, (list, tuple, set, np.ndarray, pd.Series)):
        return {str(item).upper().strip() for item in value if str(item).strip()}
    return {str(value).upper().strip()}


def _event_key(row: pd.Series) -> str:
    duplicate_group = str(row.get("duplicate_group_id") or "").strip()
    if duplicate_group:
        return duplicate_group
    external = str(row.get("external_id") or "").strip()
    if external:
        return f"{row.get('source_id', '')}:{external}"
    item_id = str(row.get("id") or "").strip()
    if item_id:
        return item_id
    return f"row:{row.name}"


def prepare_news_frame(news: pd.DataFrame) -> pd.DataFrame:
    """Normalize research news and derive a conservative knowledge timestamp.

    The current NewsItem storage keeps the latest article body, not historical
    content versions. To avoid backfilling an edit into the past, any edited row
    becomes usable only at edited_at. This is conservative: it may discard
    information that was known before the edit, but never leaks the later text.
    """
    required = {"published_at", "received_at"}
    missing = sorted(required - set(news.columns))
    if missing:
        raise ValueError(f"news frame missing required columns: {missing}")

    frame = news.copy()
    for column in ("published_at", "received_at", "known_at", "edited_at", "scheduled_at"):
        if column in frame.columns:
            frame[column] = _utc(frame[column])
    if frame["published_at"].isna().any() or frame["received_at"].isna().any():
        raise ValueError("news timestamps must be valid")

    known_candidates = [frame["published_at"], frame["received_at"]]
    for column in ("known_at", "edited_at"):
        if column in frame.columns:
            known_candidates.append(frame[column])
    known = pd.concat(known_candidates, axis=1).max(axis=1)
    frame["research_known_at"] = pd.to_datetime(known, utc=True)

    defaults: dict[str, Any] = {
        "id": "",
        "external_id": "",
        "source_id": "unknown",
        "source_name": "unknown",
        "event_type": "other",
        "sentiment": "neutral",
        "impact_direction": "uncertain",
        "crypto_relevance": 0.0,
        "impact_probability": 0.0,
        "credibility_score": 0.5,
        "uncertainty": 1.0,
        "crypto_assets": None,
        "duplicate_group_id": None,
        "is_duplicate": False,
        "novelty_score": np.nan,
    }
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default

    for column in ("event_type", "sentiment", "impact_direction", "source_id"):
        frame[column] = frame[column].astype(str).str.lower().str.strip()
    for column in ("crypto_relevance", "impact_probability", "credibility_score", "uncertainty", "novelty_score"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["crypto_relevance"] = frame["crypto_relevance"].fillna(0.0).clip(0, 1)
    frame["impact_probability"] = frame["impact_probability"].fillna(0.0).clip(0, 1)
    frame["credibility_score"] = frame["credibility_score"].fillna(0.5).clip(0, 1)
    frame["uncertainty"] = frame["uncertainty"].fillna(1.0).clip(0, 1)
    frame["event_key"] = frame.apply(_event_key, axis=1)
    frame["asset_set"] = frame["crypto_assets"].map(_assets)
    return frame.sort_values(["research_known_at", "published_at"]).reset_index(drop=True)


def _relevant(part: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if part.empty:
        return part
    base = _asset(symbol)
    exact = part["asset_set"].map(lambda values: base in values or symbol.upper() in values)
    broad = part["event_type"].isin(BROAD_EVENTS) & (part["crypto_relevance"] >= 0.20)
    market_wide = part["asset_set"].map(len).eq(0) & (part["crypto_relevance"] >= 0.70)
    return part[exact | broad | market_wide]


def _weight(part: pd.DataFrame) -> pd.Series:
    sentiment = part["sentiment"].map(SENTIMENT_VALUE).fillna(0.0)
    return (
        sentiment
        * part["crypto_relevance"]
        * part["impact_probability"]
        * part["credibility_score"]
        * (1.0 - 0.5 * part["uncertainty"])
    )


def _risk_score(part: pd.DataFrame, event_type: str) -> float:
    selected = part[part["event_type"] == event_type]
    if selected.empty:
        return 0.0
    direction = selected["impact_direction"].map(DIRECTION_RISK).fillna(0.65)
    values = (
        selected["impact_probability"]
        * selected["crypto_relevance"].clip(lower=0.25)
        * selected["credibility_score"]
        * direction
    )
    return float(np.clip(values.max(), 0.0, 1.0))


def _event_count(part: pd.DataFrame) -> int:
    if part.empty:
        return 0
    return int(part["event_key"].nunique())


def _score_asset(part: pd.DataFrame, asset: str) -> float:
    if part.empty:
        return 0.0
    selected = part[part["asset_set"].map(lambda values: asset in values)]
    if selected.empty:
        return 0.0
    weights = _weight(selected)
    denom = float(np.abs(weights).sum())
    return float(weights.sum() / denom) if denom > 1e-12 else 0.0


def _features_at(news: pd.DataFrame, timestamp: pd.Timestamp, symbol: str) -> dict[str, float]:
    available = news[
        (news["published_at"] <= timestamp)
        & (news["received_at"] <= timestamp)
        & (news["research_known_at"] <= timestamp)
    ]
    available = _relevant(available, symbol)
    result: dict[str, float] = {}

    by_window: dict[int, pd.DataFrame] = {}
    for hours in WINDOWS:
        cutoff = timestamp - pd.Timedelta(hours=hours)
        part = available[available["published_at"] >= cutoff]
        by_window[hours] = part
        result[f"news_count_{hours}h"] = float(_event_count(part))

    for hours in (1, 3, 12):
        part = by_window[hours]
        if part.empty:
            result[f"weighted_sentiment_{hours}h"] = 0.0
            continue
        weights = _weight(part)
        denom = float(np.abs(weights).sum())
        result[f"weighted_sentiment_{hours}h"] = float(weights.sum() / denom) if denom > 1e-12 else 0.0

    day = by_window[24]
    if day.empty:
        result.update(
            positive_shock_score=0.0,
            negative_shock_score=0.0,
            geopolitical_risk_score=0.0,
            regulatory_risk_score=0.0,
            macro_risk_score=0.0,
            exchange_risk_score=0.0,
            high_impact_event_count=0.0,
            independent_source_count=0.0,
            novelty_score=0.0,
            news_disagreement=0.0,
            btc_news_score=0.0,
            eth_news_score=0.0,
            asset_specific_news_score=0.0,
            time_since_high_impact_event=168.0,
            scheduled_macro_event_nearby=0.0,
        )
        return result

    signed = _weight(day)
    result["positive_shock_score"] = float(max(0.0, signed.max()))
    result["negative_shock_score"] = float(max(0.0, -signed.min()))
    result["geopolitical_risk_score"] = _risk_score(day, "geopolitical")
    result["regulatory_risk_score"] = _risk_score(day, "regulation")
    result["macro_risk_score"] = _risk_score(day, "macro")
    result["exchange_risk_score"] = _risk_score(day, "exchange")

    high = day[(day["impact_probability"] >= 0.70) & (day["crypto_relevance"] >= 0.50)]
    result["high_impact_event_count"] = float(_event_count(high))
    result["independent_source_count"] = float(day["source_id"].nunique())

    provided_novelty = day["novelty_score"].dropna()
    if len(provided_novelty):
        novelty = float(provided_novelty.clip(0, 1).mean())
    else:
        novelty = float(day["event_key"].nunique() / max(len(day), 1))
    result["novelty_score"] = novelty

    magnitude = float(np.abs(signed).sum())
    result["news_disagreement"] = float(1.0 - abs(float(signed.sum())) / magnitude) if magnitude > 1e-12 else 0.0
    result["btc_news_score"] = _score_asset(day, "BTC")
    result["eth_news_score"] = _score_asset(day, "ETH")
    result["asset_specific_news_score"] = _score_asset(day, _asset(symbol))

    if high.empty:
        result["time_since_high_impact_event"] = 168.0
    else:
        latest = high["research_known_at"].max()
        result["time_since_high_impact_event"] = float(min((timestamp - latest).total_seconds() / 3600.0, 168.0))

    if "scheduled_at" in day.columns:
        scheduled = day[
            (day["event_type"] == "macro")
            & day["scheduled_at"].notna()
            & ((day["scheduled_at"] - timestamp).abs() <= pd.Timedelta(hours=6))
        ]
        result["scheduled_macro_event_nearby"] = float(not scheduled.empty)
    else:
        result["scheduled_macro_event_nearby"] = 0.0
    return result


def merge_market_news_features(
    market: pd.DataFrame,
    news: pd.DataFrame | None,
    *,
    timestamp_column: str = "timestamp",
    symbol_column: str = "symbol",
) -> pd.DataFrame:
    """Leakage-safe market/news join.

    No production code is changed. If the news service/export is missing, all
    research news features are deterministic neutral defaults.
    """
    if timestamp_column not in market.columns or symbol_column not in market.columns:
        raise ValueError("market frame must contain timestamp and symbol")
    result = market.copy()
    result[timestamp_column] = _utc(result[timestamp_column])
    if result[timestamp_column].isna().any():
        raise ValueError("market timestamps must be valid")
    result[symbol_column] = result[symbol_column].astype(str).str.upper().str.replace("/", "", regex=False).str.replace("-", "", regex=False)

    prepared = prepare_news_frame(news) if news is not None and len(news) else None
    rows: list[dict[str, float]] = []
    for row in result[[timestamp_column, symbol_column]].itertuples(index=False, name=None):
        timestamp, symbol = row
        if prepared is None:
            features = _features_at(pd.DataFrame(columns=[
                "published_at", "received_at", "research_known_at", "event_type",
                "crypto_relevance", "asset_set", "event_key", "sentiment",
                "impact_direction", "impact_probability", "credibility_score",
                "uncertainty", "source_id", "novelty_score",
            ]), timestamp, symbol)
        else:
            features = _features_at(prepared, timestamp, symbol)
        rows.append(features)
    news_features = pd.DataFrame(rows, index=result.index)
    for column in NEWS_FEATURE_COLUMNS:
        if column not in news_features:
            news_features[column] = 0.0
    return pd.concat([result, news_features[NEWS_FEATURE_COLUMNS]], axis=1)


def _ece(y_true: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    value = 0.0
    for index in range(bins):
        if index == bins - 1:
            mask = (probability >= edges[index]) & (probability <= edges[index + 1])
        else:
            mask = (probability >= edges[index]) & (probability < edges[index + 1])
        if not mask.any():
            continue
        value += mask.mean() * abs(float(y_true[mask].mean()) - float(probability[mask].mean()))
    return float(value)


def _classification(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
    unique = np.unique(y_true)
    roc = float(roc_auc_score(y_true, probability)) if len(unique) > 1 else None
    pr = float(average_precision_score(y_true, probability)) if len(unique) > 1 else None
    return {
        "roc_auc": roc,
        "pr_auc": pr,
        "brier": float(brier_score_loss(y_true, probability)),
        "log_loss": float(log_loss(y_true, np.clip(probability, 1e-7, 1 - 1e-7), labels=[0, 1])),
        "ece": _ece(y_true, probability),
    }


def _portfolio(returns: np.ndarray, selected: np.ndarray, *, cost_multiplier: float = 1.0) -> dict[str, float | int | None]:
    selected_returns = returns[selected].astype(float)
    if len(selected_returns) == 0:
        return {
            "portfolio_return": 0.0,
            "profit_factor": None,
            "max_drawdown": 0.0,
            "sharpe": None,
            "sortino": None,
            "calmar": None,
            "trades": 0,
            "turnover": 0.0,
            "exposure": 0.0,
        }
    # net_return already contains the baseline fee/slippage contract. Cost
    # stress scales only the losing friction component conservatively.
    stressed = selected_returns - np.maximum(cost_multiplier - 1.0, 0.0) * 0.0015
    equity = np.cumprod(1.0 + stressed)
    running_max = np.maximum.accumulate(equity)
    drawdowns = equity / running_max - 1.0
    total = float(equity[-1] - 1.0)
    positive = float(stressed[stressed > 0].sum())
    negative = float(-stressed[stressed < 0].sum())
    pf = positive / negative if negative > 1e-12 else (math.inf if positive > 0 else None)
    std = float(stressed.std(ddof=1)) if len(stressed) > 1 else 0.0
    sharpe = float(stressed.mean() / std * math.sqrt(len(stressed))) if std > 1e-12 else None
    downside = stressed[stressed < 0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = float(stressed.mean() / downside_std * math.sqrt(len(stressed))) if downside_std > 1e-12 else None
    max_dd = float(drawdowns.min())
    calmar = float(total / abs(max_dd)) if max_dd < -1e-12 else None
    rate = float(selected.mean())
    return {
        "portfolio_return": total,
        "profit_factor": None if pf is None else float(pf),
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "trades": int(len(stressed)),
        "turnover": rate,
        "exposure": rate,
    }


def evaluate_probabilities(
    frame: pd.DataFrame,
    probability: Sequence[float],
    *,
    threshold: float = 0.5,
    selected_override: Sequence[bool] | None = None,
) -> dict[str, Any]:
    y = frame["target_good_trade"].to_numpy(dtype=int)
    p = np.asarray(probability, dtype=float)
    if len(p) != len(frame):
        raise ValueError("probability length mismatch")
    selected = np.asarray(selected_override, dtype=bool) if selected_override is not None else p >= threshold
    metrics = _classification(y, p)
    metrics.update(_portfolio(frame["net_return"].to_numpy(dtype=float), selected))
    metrics["threshold"] = float(threshold)
    metrics["cost_stress"] = {
        "1.0x": _portfolio(frame["net_return"].to_numpy(dtype=float), selected, cost_multiplier=1.0)["portfolio_return"],
        "1.5x": _portfolio(frame["net_return"].to_numpy(dtype=float), selected, cost_multiplier=1.5)["portfolio_return"],
        "2.0x": _portfolio(frame["net_return"].to_numpy(dtype=float), selected, cost_multiplier=2.0)["portfolio_return"],
    }
    by_symbol = {}
    if "symbol" in frame.columns:
        selected_series = pd.Series(selected, index=frame.index)
        for symbol, part in frame.groupby("symbol"):
            mask = selected_series.loc[part.index].to_numpy(dtype=bool)
            by_symbol[str(symbol)] = _portfolio(part["net_return"].to_numpy(dtype=float), mask)["portfolio_return"]
    total_abs = sum(abs(float(value)) for value in by_symbol.values())
    metrics["concentration"] = (
        max((abs(float(value)) for value in by_symbol.values()), default=0.0) / total_abs
        if total_abs > 1e-12 else 0.0
    )
    return metrics


def _prepare_x(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    result = frame[features].copy()
    for column in features:
        if pd.api.types.is_numeric_dtype(result[column]):
            result[column] = pd.to_numeric(result[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        else:
            result[column] = result[column].astype("object").where(result[column].notna(), "__missing__").astype(str)
    return result


def _preprocessor(frame: pd.DataFrame, features: list[str]) -> ColumnTransformer:
    numeric = [column for column in features if pd.api.types.is_numeric_dtype(frame[column])]
    categorical = [column for column in features if column not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", StandardScaler(), numeric))
    if categorical:
        transformers.append(("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical))
    return ColumnTransformer(transformers, remainder="drop")


def _fit_logistic(frame: pd.DataFrame, features: list[str], seed: int = 42) -> FittedModel:
    pipeline = Pipeline(
        [
            ("prepare", _preprocessor(frame, features)),
            ("model", LogisticRegression(max_iter=1000, random_state=seed, class_weight="balanced")),
        ]
    )
    x = _prepare_x(frame, features)
    y = frame["target_good_trade"].astype(int)
    pipeline.fit(x, y)
    return FittedModel("logistic", features, pipeline)


def _fit_optional(name: str, frame: pd.DataFrame, features: list[str], seed: int) -> FittedModel | None:
    x = _prepare_x(frame, features)
    y = frame["target_good_trade"].astype(int)
    if name == "catboost":
        try:
            from catboost import CatBoostClassifier
        except Exception:
            return None
        model = CatBoostClassifier(
            iterations=120,
            depth=4,
            learning_rate=0.05,
            loss_function="Logloss",
            verbose=False,
            random_seed=seed,
            allow_writing_files=False,
        )
    elif name == "xgboost":
        try:
            from xgboost import XGBClassifier
        except Exception:
            return None
        model = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=seed,
            eval_metric="logloss",
            n_jobs=1,
        )
    elif name == "lightgbm":
        try:
            from lightgbm import LGBMClassifier
        except Exception:
            return None
        model = LGBMClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            random_state=seed,
            verbosity=-1,
            n_jobs=1,
        )
    else:
        raise ValueError(f"unknown architecture: {name}")
    preprocessor = _preprocessor(frame, features)
    transformed = np.asarray(preprocessor.fit_transform(x))
    model.fit(transformed, y)
    return FittedModel(name, features, model, preprocessor)


def _candidate_models(frame: pd.DataFrame, features: list[str], seed: int) -> list[FittedModel]:
    result = [_fit_logistic(frame, features, seed)]
    for name in ("catboost", "xgboost", "lightgbm"):
        fitted = _fit_optional(name, frame, features, seed)
        if fitted is not None:
            result.append(fitted)
    return result


def chronological_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, ResearchSplit]:
    ordered = frame.sort_values("timestamp").copy()
    timestamps = pd.Index(pd.to_datetime(ordered["timestamp"], utc=True).drop_duplicates().sort_values())
    if len(timestamps) < 40:
        raise ValueError("research requires at least 40 unique timestamps")
    a = max(1, int(len(timestamps) * 0.50))
    b = max(a + 1, int(len(timestamps) * 0.65))
    c = max(b + 1, int(len(timestamps) * 0.80))
    train_t, meta_t, selection_t, final_t = timestamps[:a], timestamps[a:b], timestamps[b:c], timestamps[c:]
    parts = [ordered[ordered["timestamp"].isin(index)].copy() for index in (train_t, meta_t, selection_t, final_t)]
    if any(part.empty for part in parts):
        raise ValueError("research split produced an empty partition")
    split = ResearchSplit(
        train_end=pd.Timestamp(train_t.max()),
        meta_end=pd.Timestamp(meta_t.max()),
        selection_end=pd.Timestamp(selection_t.max()),
        final_start=pd.Timestamp(final_t.min()),
    )
    return (*parts, split)


def _selection_score(metrics: dict[str, Any]) -> float:
    pr = metrics.get("pr_auc")
    pr_value = float(pr) if pr is not None else 0.0
    return pr_value - float(metrics["brier"]) - 0.2 * float(metrics["ece"])


def _bootstrap_return(frame: pd.DataFrame, selected: np.ndarray, seeds: int = 200) -> dict[str, float | None]:
    values = frame.loc[selected, "net_return"].to_numpy(dtype=float)
    if len(values) < 3:
        return {"p05": None, "median": None, "p95": None, "positive_rate": None}
    rng = np.random.default_rng(20260925)
    block = max(2, min(12, len(values) // 5))
    results = []
    for _ in range(seeds):
        sample = []
        while len(sample) < len(values):
            start = int(rng.integers(0, max(len(values) - block + 1, 1)))
            sample.extend(values[start : start + block].tolist())
        sampled = np.asarray(sample[: len(values)])
        results.append(float(np.prod(1 + sampled) - 1))
    arr = np.asarray(results)
    return {
        "p05": float(np.quantile(arr, 0.05)),
        "median": float(np.quantile(arr, 0.50)),
        "p95": float(np.quantile(arr, 0.95)),
        "positive_rate": float((arr > 0).mean()),
    }


def _walk_forward(frame: pd.DataFrame, features: list[str], folds: int = 3) -> dict[str, Any]:
    ordered = frame.sort_values("timestamp")
    timestamps = pd.Index(pd.to_datetime(ordered["timestamp"], utc=True).drop_duplicates().sort_values())
    if len(timestamps) < 24:
        return {"folds": 0, "positive_return_rate": None, "returns": []}
    returns: list[float] = []
    boundaries = np.linspace(int(len(timestamps) * 0.45), len(timestamps), folds + 1, dtype=int)
    for index in range(folds):
        train_times = timestamps[: boundaries[index]]
        test_times = timestamps[boundaries[index] : boundaries[index + 1]]
        if len(train_times) < 10 or len(test_times) < 2:
            continue
        train = ordered[ordered["timestamp"].isin(train_times)]
        test = ordered[ordered["timestamp"].isin(test_times)]
        if train["target_good_trade"].nunique() < 2:
            continue
        model = _fit_logistic(train, features, 42 + index)
        p = model.predict_proba(test)
        returns.append(float(evaluate_probabilities(test, p)["portfolio_return"]))
    return {
        "folds": len(returns),
        "positive_return_rate": float(np.mean(np.asarray(returns) > 0)) if returns else None,
        "returns": returns,
    }


def run_news_fusion_research(
    merged: pd.DataFrame,
    *,
    price_features: Sequence[str],
    seeds: Sequence[int] = (42, 137, 271),
    evidence_scope: str = "research_only",
) -> dict[str, Any]:
    """Run the frozen MVP-6 research comparison.

    Architecture selection uses only train/meta/selection partitions. The final
    holdout is evaluated after all model/architecture choices are frozen.
    """
    required = {"timestamp", "symbol", "target_good_trade", "net_return", *price_features, *NEWS_FEATURE_COLUMNS}
    missing = sorted(required - set(merged.columns))
    if missing:
        raise ValueError(f"merged research frame missing columns: {missing}")

    frame = merged.copy()
    frame["timestamp"] = _utc(frame["timestamp"])
    frame = frame.replace([np.inf, -np.inf], np.nan)
    train, meta, selection, final, split = chronological_split(frame)
    price_features = list(price_features)
    news_features = list(NEWS_FEATURE_COLUMNS)
    fusion_features = [*price_features, *news_features]

    if train["target_good_trade"].nunique() < 2:
        raise ValueError("training partition needs both classes")

    price_model = _fit_logistic(train, price_features, 42)
    news_model = _fit_logistic(train, news_features, 42)

    architecture_trials: dict[str, dict[str, Any]] = {}
    candidates = _candidate_models(train, fusion_features, 42)
    for candidate in candidates:
        p = candidate.predict_proba(selection)
        metrics = evaluate_probabilities(selection, p)
        architecture_trials[candidate.name] = metrics
    best_name = max(architecture_trials, key=lambda name: _selection_score(architecture_trials[name]))

    # Refit selected fusion architecture on train+meta+selection only after the
    # choice is frozen. Final holdout is still untouched.
    development = pd.concat([train, meta, selection], ignore_index=True)
    if best_name == "logistic":
        fusion_model = _fit_logistic(development, fusion_features, 42)
    else:
        fusion_model = _fit_optional(best_name, development, fusion_features, 42)
        if fusion_model is None:
            fusion_model = _fit_logistic(development, fusion_features, 42)
            best_name = "logistic"

    price_model_final = _fit_logistic(development, price_features, 42)
    news_model_final = _fit_logistic(development, news_features, 42)
    price_p = price_model_final.predict_proba(final)
    news_p = news_model_final.predict_proba(final)
    fusion_p = fusion_model.predict_proba(final)

    # Stacking meta-model is trained only on the dedicated meta partition using
    # base models that were fitted on train.
    meta_price = price_model.predict_proba(meta)
    meta_news = news_model.predict_proba(meta)
    meta_x = pd.DataFrame({"price_probability": meta_price, "news_probability": meta_news})
    stack = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    stack.fit(meta_x, meta["target_good_trade"].astype(int))
    stack_p = stack.predict_proba(pd.DataFrame({"price_probability": price_p, "news_probability": news_p}))[:, 1]

    risk = final[[
        "negative_shock_score", "geopolitical_risk_score", "regulatory_risk_score",
        "macro_risk_score", "exchange_risk_score",
    ]].max(axis=1).to_numpy(dtype=float)
    overlay_p = np.clip(price_p * (1.0 - 0.25 * risk), 0.0, 1.0)
    veto = (price_p >= 0.5) & (risk < 0.75)
    context_only = price_p.copy()

    experiments = {
        "A_price_only": evaluate_probabilities(final, price_p),
        "B_news_only": evaluate_probabilities(final, news_p),
        "C_price_plus_news": evaluate_probabilities(final, fusion_p),
        "D_price_plus_news_risk_overlay": evaluate_probabilities(final, overlay_p),
        "E_stacking": evaluate_probabilities(final, stack_p),
        "F_news_veto": evaluate_probabilities(final, price_p, selected_override=veto),
        "G_news_context_only": evaluate_probabilities(final, context_only),
    }

    ablations: dict[str, dict[str, Any]] = {}
    groups = {
        "price_only": [],
        "price_plus_sentiment": ["weighted_sentiment_1h", "weighted_sentiment_3h", "weighted_sentiment_12h", "positive_shock_score", "negative_shock_score", "news_disagreement"],
        "price_plus_event_counts": ["news_count_1h", "news_count_3h", "news_count_6h", "news_count_12h", "news_count_24h", "high_impact_event_count", "independent_source_count", "novelty_score", "time_since_high_impact_event", "scheduled_macro_event_nearby"],
        "price_plus_geopolitical": ["geopolitical_risk_score"],
        "price_plus_regulatory": ["regulatory_risk_score"],
        "price_plus_all_news": news_features,
    }
    for name, extra in groups.items():
        features = [*price_features, *extra]
        model = _fit_logistic(development, features, 42)
        ablations[name] = evaluate_probabilities(final, model.predict_proba(final))

    seed_returns: list[float] = []
    for seed in seeds:
        if best_name == "logistic":
            seeded = _fit_logistic(development, fusion_features, seed)
        else:
            seeded = _fit_optional(best_name, development, fusion_features, seed) or _fit_logistic(development, fusion_features, seed)
        seeded_p = seeded.predict_proba(final)
        seed_returns.append(float(evaluate_probabilities(final, seeded_p)["portfolio_return"]))

    selected = fusion_p >= 0.5
    stability = {
        "seeds": list(seeds),
        "returns": seed_returns,
        "positive_seed_rate": float(np.mean(np.asarray(seed_returns) > 0)) if seed_returns else None,
        "return_std": float(np.std(seed_returns)) if seed_returns else None,
    }
    walk_forward = _walk_forward(development, fusion_features)
    bootstrap = _bootstrap_return(final, selected)

    price_metrics = experiments["A_price_only"]
    fusion_metrics = experiments["C_price_plus_news"]
    robust_improvement = (
        float(fusion_metrics["portfolio_return"]) > float(price_metrics["portfolio_return"])
        and (fusion_metrics["profit_factor"] or 0.0) > (price_metrics["profit_factor"] or 0.0)
        and (walk_forward["positive_return_rate"] or 0.0) >= 0.60
        and (stability["positive_seed_rate"] or 0.0) >= 0.60
        and (bootstrap["positive_rate"] or 0.0) >= 0.60
        and float(fusion_metrics["cost_stress"]["1.5x"]) > 0.0
    )

    return {
        "split": {
            "train_end": split.train_end.isoformat(),
            "meta_end": split.meta_end.isoformat(),
            "selection_end": split.selection_end.isoformat(),
            "final_start": split.final_start.isoformat(),
        },
        "best_fusion_architecture": best_name,
        "architecture_selection": architecture_trials,
        "experiments": experiments,
        "ablation": ablations,
        "walk_forward": walk_forward,
        "seed_stability": stability,
        "block_bootstrap": bootstrap,
        "dataset_improvement_observed": bool(robust_improvement),
        "evidence_scope": evidence_scope,
        "news_improvement_proven": bool(robust_improvement and evidence_scope == "real_oos"),
        "production_trade_gate_should_change": bool(robust_improvement and evidence_scope == "real_oos"),
    }
