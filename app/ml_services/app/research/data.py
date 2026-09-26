from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..training.data_validation import interval_to_timedelta

REQUIRED = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_history(frame: pd.DataFrame, *, interval: str, expected_symbols: list[str] | None = None) -> dict[str, Any]:
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"history missing required columns: {missing}")
    df = frame.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.upper().str.replace("/", "", regex=False).str.replace("-", "", regex=False)
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    numeric = df[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    invalid_ohlc = (
        df["timestamp"].isna()
        | ~np.isfinite(numeric).all(axis=1)
        | (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (df["volume"] < 0)
        | (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )
    duplicate_mask = df.duplicated(["symbol", "timestamp"], keep=False)
    delta = interval_to_timedelta(interval)
    gaps: dict[str, dict[str, Any]] = {}
    for symbol, part in df.sort_values("timestamp").groupby("symbol"):
        diffs = part["timestamp"].sort_values().diff().dropna()
        bad = diffs[diffs > delta * 1.5]
        if len(bad):
            gaps[str(symbol)] = {
                "count": int(len(bad)),
                "largest": str(bad.max()),
            }
    symbols = sorted(df["symbol"].dropna().unique().tolist())
    expected = sorted(set(expected_symbols or []))
    missing_symbols = sorted(set(expected) - set(symbols))
    return {
        "rows": int(len(df)),
        "start": str(df["timestamp"].min()),
        "end": str(df["timestamp"].max()),
        "symbols": symbols,
        "symbol_count": len(symbols),
        "missing_expected_symbols": missing_symbols,
        "duplicate_rows": int(duplicate_mask.sum()),
        "invalid_rows": int(invalid_ohlc.sum()),
        "zero_volume_rows": int((df["volume"] == 0).sum()),
        "gaps": gaps,
        "gap_symbol_count": len(gaps),
        "pass": int(duplicate_mask.sum()) == 0 and int(invalid_ohlc.sum()) == 0 and not missing_symbols,
    }


def dataframe_sha256(frame: pd.DataFrame) -> str:
    """Stable content hash for experiment lineage without writing a temp parquet."""
    digest = hashlib.sha256()
    normalized = frame.copy()
    if "timestamp" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], utc=True).astype("int64")
    normalized = normalized.sort_values(
        [column for column in ["timestamp", "symbol", "strategy_name"] if column in normalized.columns]
    ).reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(normalized, index=True).to_numpy(dtype="uint64")
    digest.update(hashed.tobytes())
    digest.update("|".join(map(str, normalized.columns)).encode("utf-8"))
    return digest.hexdigest()
