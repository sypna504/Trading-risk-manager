from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/research", tags=["research"])
ROOT = Path("runtime/research")

def _read_json(name: str):
    path = ROOT / name
    if not path.exists():
        return {"available": False, "reason": "research artifact not found"}
    return json.loads(path.read_text(encoding="utf-8"))

@router.get("/latest")
def latest():
    return _read_json("LATEST.json")

@router.get("/backtest")
def backtest():
    payload = _read_json("FINAL_METRICS.json")
    return payload.get("portfolio_backtest", payload) if isinstance(payload, dict) else payload
