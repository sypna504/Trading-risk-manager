# Trading Risk Manager — MVP-2 overlay

Base branch: `feature/news-agent-full-mvp`.

This archive is an overlay for the repository branch. Copy its contents to the
repository root, preserving paths.

## What was added

- optional Telethon Telegram adapter;
- `config/news_sources.yaml` with Telegram disabled by default;
- edit-aware Telegram identity through `source_id + external_id`;
- `NewsAnalyzer` interface;
- rule-based fallback;
- Ollama HTTP adapter with strict Pydantic JSON validation;
- fallback for timeout, provider/model errors, invalid/empty JSON;
- optional Docker Compose profile `llm`;
- offline mocked Telegram/Ollama tests;
- Telegram session files ignored by Git.

## Run tests

```bash
pytest -q tests/news/test_telegram.py tests/news/test_local_llm.py tests/news/test_source_config.py
```

## Docker

Normal stack, no Ollama required:

```bash
docker compose up -d
```

Optional Ollama service:

```bash
docker compose --profile llm up -d
```

Set your own model in local `.env`:

```env
NEWS_LLM_PROVIDER=ollama
NEWS_LLM_URL=http://ollama:11434
NEWS_LLM_MODEL=<your-local-model>
```

Telegram stays optional and disabled in `config/news_sources.yaml` until you
explicitly enable it and provide credentials in local `.env`.
