# Trading Risk Manager — MVP-3 patch

Overlay for branch `feature/news-agent-full-mvp` containing MVP-1 + MVP-2 + MVP-3 changes.

## MVP-3

- decision-time-safe `get_market_news_context(symbol, now)`
- 24h symbol/market news summary with sentiment and risk scores
- strict `published_at <= decision_time` protection
- optional `news_context` in `/api/v1/trading/decision`
- informational reason suffix with explicit ML-gate disclaimer
- persisted decision snapshot:
  - `news_context_available`
  - `news_risk_level`
  - `news_count`
  - `high_impact_news_count`
- SQLite migration for existing decision databases
- news never changes prediction, threshold, trade gate or risk sizing

Apply by extracting the archive into the repository root with file replacement.

Recommended verification after applying to the full repo:

```bash
pytest -q tests/news tests/smoke/test_trade_decision_news_context.py
```

MVP-3 stops here. Frontend is not implemented.
