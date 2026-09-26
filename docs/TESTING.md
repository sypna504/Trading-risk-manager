# Testing

CI is split into compile, backend, ML, research, synthetic AutoML, news, agent/paper, frontend, Docker build, Docker integration and E2E jobs. Telegram and Ollama live calls are excluded from CI. Local environments without Docker/npm dependencies report those checks as NOT RUN rather than faking a PASS.
