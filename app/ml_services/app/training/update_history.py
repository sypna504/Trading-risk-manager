from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .data_validation import (
    interval_to_timedelta,
    normalize_history_frame,
    validate_history,
)
from .training_config import TrainingConfig


OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def to_ccxt_symbol(symbol: str) -> str:
    normalized = symbol.upper().replace("/", "").replace("-", "")
    for quote in ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return f"{normalized[:-len(quote)]}/{quote}"
    raise ValueError(f"cannot convert symbol to ccxt format: {symbol}")


def last_closed_open_time(now: pd.Timestamp, interval: str) -> pd.Timestamp:
    current = pd.to_datetime(now, utc=True)
    delta = interval_to_timedelta(interval)
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    elapsed = current - epoch
    current_open = epoch + (elapsed // delta) * delta
    return current_open - delta


def _create_exchange(config: TrainingConfig):
    try:
        import ccxt
    except ImportError as error:
        raise RuntimeError("ccxt is required for history updates") from error

    exchange_class = getattr(ccxt, config.exchange, None)
    if exchange_class is None:
        raise ValueError(f"unsupported exchange: {config.exchange}")
    return exchange_class(
        {
            "enableRateLimit": True,
            "timeout": config.request_timeout * 1000,
        }
    )


def _fetch_symbol_history(
    exchange: Any,
    symbol: str,
    config: TrainingConfig,
    start_timestamp: pd.Timestamp,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    ccxt_symbol = to_ccxt_symbol(symbol)
    if ccxt_symbol not in exchange.markets:
        raise ValueError(f"symbol is not available on {config.exchange}: {ccxt_symbol}")

    step = interval_to_timedelta(config.interval)
    since_ms = int(pd.to_datetime(start_timestamp, utc=True).timestamp() * 1000)
    cutoff_ms = int(pd.to_datetime(cutoff, utc=True).timestamp() * 1000)
    all_rows: list[list[float]] = []
    previous_last_ms: int | None = None

    while since_ms <= cutoff_ms:
        page = exchange.fetch_ohlcv(
            ccxt_symbol,
            timeframe=config.interval,
            since=since_ms,
            limit=config.request_limit,
        )
        if not page:
            break

        all_rows.extend(page)
        last_ms = int(page[-1][0])
        if previous_last_ms is not None and last_ms <= previous_last_ms:
            break
        previous_last_ms = last_ms
        since_ms = last_ms + int(step.total_seconds() * 1000)

        if last_ms >= cutoff_ms or len(page) < config.request_limit:
            break
        if getattr(exchange, "rateLimit", 0):
            time.sleep(float(exchange.rateLimit) / 1000.0)

    if not all_rows:
        return pd.DataFrame(columns=[*OHLCV_COLUMNS, "symbol"])

    result = pd.DataFrame(all_rows, columns=OHLCV_COLUMNS)
    result["timestamp"] = pd.to_datetime(result["timestamp"], unit="ms", utc=True)
    result["symbol"] = symbol.upper().replace("/", "").replace("-", "")
    result = result[result["timestamp"] <= cutoff]
    return result


def merge_history(old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    frames = [frame for frame in (old_df, new_df) if frame is not None and not frame.empty]
    if not frames:
        return pd.DataFrame(columns=[*OHLCV_COLUMNS, "symbol"])

    combined = pd.concat(frames, ignore_index=True)
    combined = normalize_history_frame(combined)
    combined = combined.drop_duplicates(
        subset=["symbol", "timestamp"],
        keep="last",
    )
    return combined.sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        df.to_parquet(temporary, index=False)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _frame_hash(df: pd.DataFrame) -> str:
    if df.empty:
        return hashlib.sha256(b"").hexdigest()
    ordered = df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(ordered, index=False).to_numpy().tobytes()
    return hashlib.sha256(hashed).hexdigest()


def update_history(
    config: TrainingConfig | None = None,
    exchange_factory: Callable[[TrainingConfig], Any] | None = None,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    config = config or TrainingConfig.from_env()
    current_time = pd.Timestamp.now(tz="UTC") if now is None else pd.to_datetime(now, utc=True)
    cutoff = last_closed_open_time(current_time, config.interval)

    if config.history_path.exists():
        old_df = normalize_history_frame(pd.read_parquet(config.history_path))
    else:
        old_df = pd.DataFrame(columns=[*OHLCV_COLUMNS, "symbol"])

    configured_symbols = {
        symbol.upper().replace("/", "").replace("-", "")
        for symbol in config.symbols
    }
    existing_symbols = set(old_df["symbol"].unique()) if not old_df.empty else set()
    history_only_symbols = sorted(existing_symbols - configured_symbols)

    if history_only_symbols and config.history_symbol_policy == "filter":
        old_df = old_df[old_df["symbol"].isin(configured_symbols)].reset_index(drop=True)
        existing_symbols = set(old_df["symbol"].unique()) if not old_df.empty else set()
        history_only_symbols = []

    if config.history_symbol_policy == "extend":
        validation_symbols = sorted(configured_symbols | existing_symbols)
        fetch_symbols = validation_symbols
    else:
        validation_symbols = sorted(configured_symbols)
        fetch_symbols = validation_symbols

    exchange = (exchange_factory or _create_exchange)(config)
    exchange.load_markets()

    new_parts: list[pd.DataFrame] = []
    failed_symbols: dict[str, str] = {}
    interval_delta = interval_to_timedelta(config.interval)

    for symbol in fetch_symbols:
        normalized_symbol = symbol.upper().replace("/", "").replace("-", "")
        old_symbol = old_df[old_df["symbol"] == normalized_symbol]
        if old_symbol.empty:
            bars_from_window = int(
                pd.Timedelta(days=config.training_window_days) / interval_delta
            )
            requested_bars = max(config.minimum_history_rows, bars_from_window + 250)
            start = cutoff - requested_bars * interval_delta
        else:
            start = old_symbol["timestamp"].max()

        if start > cutoff:
            continue

        try:
            part = _fetch_symbol_history(
                exchange=exchange,
                symbol=normalized_symbol,
                config=config,
                start_timestamp=start,
                cutoff=cutoff,
            )
            if not part.empty:
                new_parts.append(part)
        except Exception as error:  # one bad market must not destroy all updates
            failed_symbols[normalized_symbol] = str(error)

    new_df = (
        pd.concat(new_parts, ignore_index=True)
        if new_parts
        else pd.DataFrame(columns=[*OHLCV_COLUMNS, "symbol"])
    )
    merged = merge_history(old_df, new_df)
    merged = merged[merged["timestamp"] <= cutoff].reset_index(drop=True)

    validation = validate_history(
        merged,
        allowed_symbols=validation_symbols,
        interval=config.interval,
        closed_candle_cutoff=cutoff,
        minimum_rows_per_symbol=config.minimum_history_rows,
    )
    if not validation.valid:
        raise ValueError(
            "history validation failed: " + "; ".join(validation.report["errors"])
        )

    old_keys = set(zip(old_df.get("symbol", []), old_df.get("timestamp", [])))
    merged_keys = set(zip(merged["symbol"], merged["timestamp"]))
    added_rows = len(merged_keys - old_keys)

    updated_rows = 0
    if not old_df.empty:
        value_columns = ["open", "high", "low", "close", "volume"]
        old_indexed = old_df.set_index(["symbol", "timestamp"])[value_columns]
        merged_indexed = merged.set_index(["symbol", "timestamp"])[value_columns]
        common_index = old_indexed.index.intersection(merged_indexed.index)
        if len(common_index):
            old_values = old_indexed.loc[common_index].sort_index()
            new_values = merged_indexed.loc[common_index].sort_index()
            updated_rows = int((old_values != new_values).any(axis=1).sum())

    _atomic_write_parquet(merged, config.history_path)
    report = {
        "history_path": str(config.history_path),
        "exchange": config.exchange,
        "interval": config.interval,
        "cutoff": cutoff.isoformat(),
        "old_rows": int(len(old_df)),
        "new_downloaded_rows": int(len(new_df)),
        "added_unique_rows": int(added_rows),
        "updated_existing_rows": int(updated_rows),
        "changed_rows": int(added_rows + updated_rows),
        "final_rows": int(len(merged)),
        "history_hash": _frame_hash(merged),
        "configured_symbols": sorted(configured_symbols),
        "fetch_symbols": fetch_symbols,
        "history_only_symbols": history_only_symbols,
        "history_symbol_policy": config.history_symbol_policy,
        "failed_symbols": failed_symbols,
        "validation": validation.report,
    }
    report_path = config.reports_path / "latest_history_update.json"
    _atomic_write_json(report, report_path)
    return report


if __name__ == "__main__":
    result = update_history()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
