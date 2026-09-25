# Trading Risk Manager — MVP

Research / paper-trading dashboard: market signal → ML quality gate → risk sizing → decision snapshot, with an informational news-intelligence layer. **News never changes `trade_allowed`, probability, threshold, stop-loss/take-profit or position sizing.**

## Quick start

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d
```

Open: `http://localhost:8000/`

## URLs

- Dashboard: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Model info: `http://localhost:8000/api/v1/ml/model-info`
- Trading decision: `http://localhost:8000/api/v1/trading/decision`
- Decision history: `http://localhost:8000/api/v1/trading/decisions`
- News: `http://localhost:8000/api/v1/news`
- News summary: `http://localhost:8000/api/v1/news/summary`

## Tests

Official entrypoint:

```bash
python scripts/test_all.py
```

Focused suites:

```bash
python -m pytest -q tests/regression
PYTHONPATH=app/ml_services python -m pytest -q app/ml_services/app/training/tests
python -m pytest -q tests/news tests/frontend
python -m pytest -q tests/integration/test_synthetic_e2e.py
```

## Docker validation

```bash
docker compose config
docker compose build backend ml_service
docker compose up -d backend ml_service
docker compose ps
```

The default stack does **not** require Ollama or Telegram.

## News

News is normalized, analyzed, deduplicated and persisted separately from the Quant ML gate. The trading API receives a decision-time-safe 24h context snapshot. Only `published_at <= decision_time` is used.

### Optional Telegram

Set locally in `.env`:

```text
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION_PATH=/app/data/telegram.session
```

Do not commit credentials. Without credentials Telegram is skipped and the news service continues to work.

### Optional Ollama

Set:

```text
NEWS_LLM_PROVIDER=ollama
NEWS_LLM_MODEL=<local-model-name>
NEWS_LLM_URL=http://ollama:11434
```

Start the optional service:

```bash
docker compose --profile llm up -d
```

If Ollama is unavailable, times out or returns invalid JSON, the analyzer falls back to the rule-based implementation.

## Health states

The dashboard reports Backend, ML Service, News Service and LLM as `ready`, `degraded` or `optional unavailable`. LLM unavailability is not fatal in the default configuration.

## Security

External news text is rendered with DOM `textContent`; the dashboard does not use unsafe `innerHTML` for news. External links are restricted to HTTP/HTTPS.

## Limitations

- paper/research trading only; no order execution;
- live Binance, live Telegram and live Ollama are optional environment checks and are not required by offline CI;
- news is informational only and is deliberately isolated from the trading gate;
- model quality still depends on the active validated model bundle and its data contract;
- no price+news joint training is included in this MVP.
