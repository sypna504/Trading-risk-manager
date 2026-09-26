# NEWS FEATURE ABLATION — MVP-6

## Scope

This report is from the deterministic **synthetic** MVP-6 validation fixture. It validates the research pipeline and leakage controls; it does **not** prove real trading edge.

| Feature set | PR AUC | Brier | Portfolio return | Profit factor |
|---|---:|---:|---:|---:|
| price-only | 0.8444 | 0.1597 | 45.30% | 5.4195 |
| price + sentiment | 0.8849 | 0.1441 | 48.62% | 5.9791 |
| price + event counts | 0.8493 | 0.1601 | 44.66% | 5.7568 |
| price + geopolitical | 0.8444 | 0.1597 | 45.30% | 5.4195 |
| price + regulatory | 0.8456 | 0.1595 | 45.30% | 5.4195 |
| price + all news | 0.8831 | 0.1449 | 46.94% | 5.8364 |

Synthetic fixture observation: the sentiment block contributes the largest incremental result in this artificial dataset. This is **not evidence** that sentiment improves the real strategy.

Production conclusion: **no change**.
