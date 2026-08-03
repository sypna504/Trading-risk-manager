from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_HISTORY_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
]


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    report: dict[str, Any]


def interval_to_timedelta(interval: str) -> pd.Timedelta:
    value = interval.strip().lower()
    unit = value[-1]
    amount = int(value[:-1])
    unit_map = {
        "m": "min",
        "h": "h",
        "d": "d",
        "w": "w",
    }
    if unit not in unit_map:
        raise ValueError(f"unsupported interval: {interval}")
    return pd.Timedelta(amount, unit=unit_map[unit])


def normalize_history_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    missing = [column for column in REQUIRED_HISTORY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing history columns: {missing}")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame["symbol"] = (
        frame["symbol"]
        .astype(str)
        .str.upper()
        .str.replace("/", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    return frame


def find_time_gaps(df: pd.DataFrame, interval: str) -> dict[str, list[dict[str, Any]]]:
    expected = interval_to_timedelta(interval)
    gaps: dict[str, list[dict[str, Any]]] = {}

    for symbol, part in df.groupby("symbol", sort=True):
        ordered = part.sort_values("timestamp")
        differences = ordered["timestamp"].diff()
        bad_positions = differences[differences > expected]
        if bad_positions.empty:
            continue

        symbol_gaps: list[dict[str, Any]] = []
        for index, difference in bad_positions.items():
            previous_index = ordered.index.get_loc(index) - 1
            previous_timestamp = ordered.iloc[previous_index]["timestamp"]
            current_timestamp = ordered.loc[index, "timestamp"]
            missing_bars = max(int(difference / expected) - 1, 1)
            symbol_gaps.append(
                {
                    "from": previous_timestamp.isoformat(),
                    "to": current_timestamp.isoformat(),
                    "missing_bars": missing_bars,
                }
            )
        gaps[symbol] = symbol_gaps

    return gaps


def validate_history(
    df: pd.DataFrame,
    allowed_symbols: list[str],
    interval: str,
    closed_candle_cutoff: pd.Timestamp | None = None,
    minimum_rows_per_symbol: int = 1,
) -> ValidationResult:
    report: dict[str, Any] = {"errors": [], "warnings": []}

    try:
        frame = normalize_history_frame(df)
    except ValueError as error:
        return ValidationResult(False, {"errors": [str(error)], "warnings": []})

    required = REQUIRED_HISTORY_COLUMNS
    null_counts = frame[required].isna().sum()
    report["null_counts"] = {key: int(value) for key, value in null_counts.items()}
    if int(null_counts.sum()) > 0:
        report["errors"].append("required fields contain null values")

    numeric = frame[["open", "high", "low", "close", "volume"]]
    inf_count = int(np.isinf(numeric.to_numpy(dtype=float)).sum())
    report["inf_count"] = inf_count
    if inf_count:
        report["errors"].append("numeric fields contain inf values")

    duplicate_count = int(frame.duplicated(["symbol", "timestamp"]).sum())
    report["duplicate_count"] = duplicate_count
    if duplicate_count:
        report["errors"].append("duplicate symbol+timestamp rows found")

    invalid_positive = int(
        ((frame[["open", "high", "low", "close"]] <= 0).any(axis=1)).sum()
    )
    negative_volume = int((frame["volume"] < 0).sum())
    invalid_high = int(
        (
            (frame["high"] < frame["open"])
            | (frame["high"] < frame["close"])
            | (frame["high"] < frame["low"])
        ).sum()
    )
    invalid_low = int(
        (
            (frame["low"] > frame["open"])
            | (frame["low"] > frame["close"])
            | (frame["low"] > frame["high"])
        ).sum()
    )

    report.update(
        {
            "invalid_positive_ohlc": invalid_positive,
            "negative_volume": negative_volume,
            "invalid_high": invalid_high,
            "invalid_low": invalid_low,
        }
    )
    if invalid_positive or negative_volume or invalid_high or invalid_low:
        report["errors"].append("OHLCV invariants failed")

    normalized_allowed = {
        symbol.upper().replace("/", "").replace("-", "") for symbol in allowed_symbols
    }
    unknown_symbols = sorted(set(frame["symbol"]) - normalized_allowed)
    report["unknown_symbols"] = unknown_symbols
    if unknown_symbols:
        report["errors"].append(f"unknown symbols found: {unknown_symbols}")

    if closed_candle_cutoff is not None:
        cutoff = pd.to_datetime(closed_candle_cutoff, utc=True)
        unclosed_count = int((frame["timestamp"] > cutoff).sum())
    else:
        unclosed_count = 0
    report["unclosed_candle_count"] = unclosed_count
    if unclosed_count:
        report["errors"].append("unclosed candles found")

    rows_by_symbol = frame.groupby("symbol").size().sort_index()
    report["rows_by_symbol"] = {key: int(value) for key, value in rows_by_symbol.items()}
    too_short = rows_by_symbol[rows_by_symbol < minimum_rows_per_symbol]
    if not too_short.empty:
        report["errors"].append(
            "insufficient rows for symbols: "
            + ", ".join(f"{symbol}={count}" for symbol, count in too_short.items())
        )

    sorted_copy = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    report["is_sorted"] = bool(frame.reset_index(drop=True).equals(sorted_copy))
    if not report["is_sorted"]:
        report["errors"].append("history is not sorted by symbol and timestamp")

    gaps = find_time_gaps(frame, interval)
    report["gaps"] = gaps
    report["gap_count"] = int(sum(len(items) for items in gaps.values()))
    if gaps:
        report["warnings"].append("time gaps detected; see gaps section")

    report["rows"] = int(len(frame))
    report["symbols"] = sorted(frame["symbol"].unique().tolist())
    report["min_timestamp"] = (
        frame["timestamp"].min().isoformat() if not frame.empty else None
    )
    report["max_timestamp"] = (
        frame["timestamp"].max().isoformat() if not frame.empty else None
    )

    return ValidationResult(not report["errors"], report)


def validate_dataset(
    dataset: pd.DataFrame,
    minimum_rows: int,
    minimum_class_rows: int,
) -> ValidationResult:
    required = {
        "timestamp",
        "symbol",
        "strategy_name",
        "target_good_trade",
        "net_return",
        "max_drawdown",
    }
    missing = sorted(required - set(dataset.columns))
    report: dict[str, Any] = {"errors": [], "warnings": []}
    if missing:
        report["errors"].append(f"missing dataset columns: {missing}")
        return ValidationResult(False, report)

    frame = dataset.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    report["rows"] = int(len(frame))
    report["positive_rate"] = float(frame["target_good_trade"].mean()) if len(frame) else 0.0
    report["class_counts"] = {
        str(key): int(value)
        for key, value in frame["target_good_trade"].value_counts().sort_index().items()
    }
    report["rows_by_strategy"] = {
        str(key): int(value)
        for key, value in frame.groupby("strategy_name").size().sort_index().items()
    }
    report["rows_by_symbol"] = {
        str(key): int(value)
        for key, value in frame.groupby("symbol").size().sort_index().items()
    }

    if len(frame) < minimum_rows:
        report["errors"].append(
            f"dataset too small: {len(frame)} < {minimum_rows}"
        )

    counts = frame["target_good_trade"].value_counts()
    for target in (0, 1):
        if int(counts.get(target, 0)) < minimum_class_rows:
            report["errors"].append(
                f"class {target} has fewer than {minimum_class_rows} rows"
            )

    numeric_columns = ["net_return", "max_drawdown"]
    numeric_values = frame[numeric_columns].to_numpy(dtype=float)
    if np.isnan(numeric_values).any() or np.isinf(numeric_values).any():
        report["errors"].append("dataset contains NaN or inf in outcome fields")

    duplicate_signals = int(
        frame.duplicated(["timestamp", "symbol", "strategy_name"]).sum()
    )
    report["duplicate_signals"] = duplicate_signals
    if duplicate_signals:
        report["errors"].append("duplicate strategy signals found")

    if frame["timestamp"].isna().any():
        report["errors"].append("dataset contains invalid timestamps")

    return ValidationResult(not report["errors"], report)
