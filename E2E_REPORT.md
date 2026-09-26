# E2E report

Synthetic full-platform E2E: **PASS**. The fixture flow covers market/signal contract -> deterministic ML fixture -> real risk calculation -> stored leakage-safe news context -> geopolitical context -> frozen decision gate -> paper next-bar-open position -> future candle -> TP/SL/timeout/PnL -> separate synthetic outcome -> grounded read-only agent -> frontend API contract.

The E2E explicitly asserts that news does not change `trade_allowed` and that real trading remains disabled. Live Binance/Telegram/Ollama are **NOT RUN**.
