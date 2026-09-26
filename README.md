# Trading Risk Manager — research & paper-trading platform

A crypto research platform with a frozen Quant Core, leakage-safe news research, geopolitical event analysis, read-only analytical agent, React dashboard and simulated paper portfolio. **Real trading is disabled.**

## Quick start

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Open:
- React UI: `http://localhost:3000/`
- Backend Swagger: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/api/v1/health`
- News service: `http://localhost:8010/health`

## Optional integrations

Telegram is optional; leave `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` empty to disable it. Ollama is optional and starts only with `docker compose --profile llm up -d ollama`. No live Telegram/Ollama call is required in CI.

## Tests

Python: `python scripts/test_all.py` plus focused `pytest` suites. Frontend: `cd app/frontend && npm install && npm test && npm run build`. Docker integration is split into its own CI job.

## News / fusion rule

MVP-6 implemented leakage-safe price+news research, but real OOS improvement is **NOT PROVEN**. Therefore news and geopolitical context stay informational and do not modify `trade_allowed`, model probability, threshold or risk sizing.

## Paper trading

Virtual execution follows the research contract: next-bar-open entry, simulated slippage/fees, SL/TP/timeout and conservative same-bar ambiguity handling. Model outcome monitoring and paper execution are separate systems.

## Limitations

Real exchange orders are not implemented. Real historical news/geopolitical OOS evidence is still required before any news-based production gating. Local LLM output is not treated as a factual source. See `KNOWN_LIMITATIONS.md`.
