from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
        if not pd.notna(numeric):
            return "N/A"
        return f"{numeric:.{digits}f}"
    except Exception:
        return str(value)


def header(title: str, meta: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in meta.items():
        lines.append(f"- **{key}:** {value}")
    lines.append("")
    return "\n".join(lines)


def experiment_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    columns = [
        "experiment_id", "phase", "target", "feature_set", "architecture", "class_weight",
        "parameters", "seed", "roc_auc", "pr_auc", "pr_baseline", "brier", "trades",
        "profit_factor", "portfolio_return", "max_drawdown", "cost_1_5x", "cost_2x", "score", "error",
    ]
    return pd.DataFrame(rows, columns=columns)
