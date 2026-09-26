# Apply final MVP-7 → MVP-10 overlay

Baseline: repository `sypna504/Trading-risk-manager`, branch `feature/news-agent-full-mvp`, with MVP-1..5 and MVP-6 applied.

1. Extract the ZIP contents directly into the repository root with replacement.
2. Run `python APPLY_FINAL.py` once. It applies the known pandas/CatBoost MVP-5 regression fix if the full base files are present and removes a stale `.rej` file if present.
3. Run Python tests and frontend/Docker validation as separate passes.

Recommended:

```bash
python APPLY_FINAL.py
python scripts/test_all.py
cd app/frontend && npm install && npm test && npm run build && cd ../..
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
```

Open `http://localhost:3000/`. Backend Swagger is `http://localhost:8000/docs`. No real trading endpoint is included.
