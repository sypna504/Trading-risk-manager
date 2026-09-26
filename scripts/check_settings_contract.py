from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app/backend/api/app"
CONFIG = BACKEND / "config.py"


def declared_settings() -> set[str]:
    tree = ast.parse(CONFIG.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            names: set[str] = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.add(item.target.id)
            return names
    raise RuntimeError("Settings class not found")


def referenced_settings() -> set[str]:
    names: set[str] = set()
    pattern = re.compile(r"\bsettings\.([A-Z][A-Z0-9_]*)\b")
    for path in BACKEND.rglob("*.py"):
        if path == CONFIG:
            continue
        names.update(pattern.findall(path.read_text(encoding="utf-8")))
    return names


def main() -> int:
    declared = declared_settings()
    referenced = referenced_settings()
    missing = sorted(referenced - declared)
    if missing:
        raise SystemExit("missing Settings fields: " + ", ".join(missing))
    required_outcome = {
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
    }
    missing_outcome = sorted(required_outcome - declared)
    if missing_outcome:
        raise SystemExit("outcome Settings contract missing: " + ", ".join(missing_outcome))
    print(f"settings contract: OK ({len(referenced)} referenced fields)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
