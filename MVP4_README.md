# Trading Risk Manager — MVP-4 overlay

Base: `feature/news-agent-full-mvp` + MVP-1/MVP-2/MVP-3.

This archive is an overlay. Extract it into the repository root with file replacement enabled.

## What MVP-4 adds

- vanilla HTML/CSS/JS dashboard; no React;
- model block: version, status, schema, supported interval, model age;
- decision block: signal, ML probabilities, threshold, prices, SL/TP, position size and risk;
- news context block with 24h summary and top 5 events;
- decision history including news risk and outcome status;
- system health block for Backend, ML Service, News Service and optional LLM;
- safe DOM rendering using `textContent`/DOM nodes only;
- HTTP/HTTPS validation before external news URLs become clickable;
- explicit UTF-8 reads in frontend regression tests.

## Run

```bash
docker compose up -d
```

Optional Ollama profile remains optional:

```bash
docker compose --profile llm up -d
```

Then open the backend root page, normally `http://localhost:8000/`.

## Tests executed for this checkpoint

```bash
node --check app/backend/api/app/static/app.js
pytest -q tests/news tests/frontend
python -m py_compile app/backend/api/app/routers/health_router.py app/backend/api/app/schemas/trade_decision_schemas.py app/news_intelligence/context.py
```

Result: 49/49 pytest tests passed (11 frontend + 38 news).

MVP-4 stops here. Price+news training is not included.
