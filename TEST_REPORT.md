# Final test report

Executed in the packaging environment:

- Python compileall (`app`, `tests`, `scripts`): **PASS**
- Local regression/source/E2E selection: **99/99 PASS**
  - news: 38/38
  - legacy frontend regression: 11/11
  - MVP-6 news research: 13/13
  - React source contracts: 8/8
  - geopolitical: 7/7
  - agent: 6/6
  - paper: 8/8
  - final contracts: 7/7
  - full-platform synthetic E2E: 1/1
- TypeScript transpile/syntax check: **PASS**
- Compose/CI/CD YAML consistency: **PASS**
- MVP-6 synthetic fusion script: **PASS**
- MVP-8 geopolitical synthetic script: **PASS**
- MVP-10 synthetic E2E script: **PASS**

Not run in this environment:

- full Quant training suite on a complete repository checkout; Quant Core is unchanged by MVP-7..10 and the MVP-5 regression patch is included;
- `npm install`/Vitest/Vite build: npm registry access timed out;
- Docker build/runtime: Docker CLI is unavailable;
- live Binance, Telegram and Ollama.
