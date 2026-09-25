from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_news_layer_is_not_wired_into_trade_decision():
    source = (ROOT / "app/backend/api/app/routers/trade_decision_router.py").read_text(
        encoding="utf-8"
    )
    assert "news_intelligence" not in source
    assert "news veto" not in source.lower()
    assert "news multiplier" not in source.lower()
