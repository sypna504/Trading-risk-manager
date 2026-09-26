# Trading Risk Manager architecture

The platform is research/paper-trading only. Real exchange order execution is intentionally absent.

## Runtime

- `backend`: FastAPI decision, monitoring, events, agent and paper APIs.
- `ml_service`: gRPC inference for the frozen Quant Core.
- `ml_trainer`: profile-only research/training worker.
- `news_service`: optional-independent news API over the shared news database.
- `frontend`: React + TypeScript + Vite dashboard.
- `ollama`: optional local LLM profile.
- `postgres`: optional profile; SQLite remains the default MVP store.

## Safety boundaries

1. MVP-6 did not prove real OOS news improvement, so news/geopolitical context does not alter `trade_allowed`.
2. The analytical agent exposes only read-only tools.
3. Paper execution consumes an already-created decision; it cannot change model probability, threshold or risk gates.
4. Paper entry follows `next_bar_open`; signal close is never treated as the realized virtual fill.
5. Outcome evaluation and paper execution use separate tables/services.
