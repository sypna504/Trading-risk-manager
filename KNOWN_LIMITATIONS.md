# Known limitations

1. Real OOS news improvement: NOT PROVEN.
2. Real OOS geopolitical improvement: NOT PROVEN.
3. News/geopolitical context does not affect `trade_allowed`.
4. Live Binance/Telegram/Ollama tests are not required and were not run in the packaging environment.
5. Docker CLI is unavailable in the packaging environment; CI definitions cover build/runtime.
6. Frontend dependency installation/build requires npm registry access; source contracts and TypeScript syntax are checked locally.
7. Paper trading is simulation only; no real order endpoint exists.
8. OHLC same-bar TP/SL ambiguity uses conservative stop-loss priority unless more granular data is supplied.
