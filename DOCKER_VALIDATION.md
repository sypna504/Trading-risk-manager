# Docker validation

Static compose validation: **PASS**. Services present: backend, ml_service, ml_trainer, news_service, frontend; optional profiles: ollama and postgres. Backend does not depend on Ollama/Telegram credentials.

Docker CLI is not installed in the packaging environment, therefore `docker compose build/up` is **NOT RUN** here. Final CI contains separate Docker build and Docker integration jobs.
