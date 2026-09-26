# Deployment

Quick start:

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Open `http://localhost:3000/` for React UI and `http://localhost:8000/docs` for backend Swagger. Optional Ollama: `docker compose --profile llm up -d ollama`. Optional PostgreSQL profile exists but is not required. Tag `v*` triggers image build/push workflow for backend, ml_service, news_service and frontend only; no real trading service exists.
