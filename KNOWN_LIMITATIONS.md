# Known Limitations — MVP-5

1. The application is research/paper-trading only and does not execute orders.
2. News is informational and never changes the Quant ML trading gate.
3. Telegram requires user credentials and is optional.
4. Ollama requires a local model and is optional; rule-based fallback remains available.
5. Live Binance, Telegram and Ollama are not part of deterministic CI.
6. No price+news joint model training is included.
7. Docker runtime could not be executed in this ChatGPT sandbox because Docker CLI is unavailable; the current repository's GitHub Actions Docker build is PASS.
8. This environment's GitHub connection can read the repository but cannot commit CI/docs/regression fixes (`403 Resource not accessible by integration`). The included files therefore need to be applied to the branch before a final green CI artifact can be produced.
