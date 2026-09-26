# NEWS FUSION REPORT — MVP-6

## Evidence status

The available repository does not contain a point-in-time historical news corpus aligned with the market training history. Therefore this checkpoint validates the implementation on a deterministic synthetic fixture and **does not claim real OOS improvement**.

| Experiment | ROC AUC | PR AUC | Brier | LogLoss | Return | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. price-only | 0.8505 | 0.8444 | 0.1597 | 0.4808 | 45.30% | 5.4195 | -1.63% |
| B. news-only | 0.7383 | 0.7383 | 0.2119 | 0.6044 | 36.31% | 3.1748 | -5.32% |
| C. price + news | 0.8806 | 0.8831 | 0.1449 | 0.4394 | 46.94% | 5.8364 | -1.35% |
| D. risk overlay | 0.8491 | 0.8306 | 0.1593 | 0.4842 | 41.91% | 5.5092 | -1.99% |
| E. stacking | 0.8557 | 0.8658 | 0.1592 | 0.4891 | 41.22% | 3.9060 | -2.24% |
| F. news veto | 0.8505 | 0.8444 | 0.1597 | 0.4808 | 45.30% | 5.4195 | -1.63% |
| G. context only | 0.8505 | 0.8444 | 0.1597 | 0.4808 | 45.30% | 5.4195 | -1.63% |

Best fusion architecture on the synthetic selection partition: **logistic**.

Synthetic walk-forward positive-return rate: **100.00%** (3 folds).

Synthetic seed positive-return rate: **100.00%**.

Synthetic block-bootstrap positive-return rate: **100.00%**.

The synthetic fixture shows an internally consistent fusion uplift, but `evidence_scope=research_only`, therefore:

```text
News improvement: NOT PROVEN
Production trade gate change: NO
```

The production model remains price-only. News remains informational until a real point-in-time news history demonstrates stable OOS improvement under walk-forward, bootstrap, cost stress and concentration checks.
