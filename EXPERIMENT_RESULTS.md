# Experiment Results

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Actually executed synthetic research

- total experiments: **17**
- phase counts: `{"architecture": 4, "class_weight": 3, "feature": 4, "regression_target": 1, "seed_stability": 1, "target": 2, "tuning": 2}`
- final synthetic result: **NO ROBUST EDGE FOUND**
- real Binance experiments: **NOT RUN**

| experiment_id | phase | target | feature_set | architecture | roc_auc | pr_auc | portfolio_return | profit_factor | error |
|---|---|---|---|---|---|---|---|---|---|
| exp_0001 | target | ft_atr100_r10_3h | production_full | pooled | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |
| exp_0002 | target | ft_atr100_r10_3h | production_full | pooled | 0.416667 | 0.241913 | -0.011053 | 0.590931 |  |
| exp_0003 | regression_target | future_net_return_regression | production_full | catboost_regressor |  |  | -0.010376 | 0.319258 |  |
| exp_0004 | feature | ft_atr100_r10_3h | production_full | pooled | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |
| exp_0005 | feature | ft_atr100_r10_3h | minus_volume | pooled | 0.404040 | 0.225514 | -0.018191 | 0.340398 |  |
| exp_0006 | feature | ft_atr100_r10_3h | minus_identity | pooled | 0.416667 | 0.236255 | 0.000017 | 1.000654 |  |
| exp_0007 | feature | ft_atr100_r10_3h | production_plus_btc | pooled | 0.391414 | 0.228587 | -0.011867 | 0.560365 |  |
| exp_0008 | architecture | ft_atr100_r10_3h | production_full | pooled | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |
| exp_0009 | architecture | ft_atr100_r10_3h | production_full | separate_strategy | 0.381313 | 0.232261 | -0.010747 | 0.592904 |  |
| exp_0010 | architecture | ft_atr100_r10_3h | production_full | separate_symbol | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |
| exp_0011 | architecture | ft_atr100_r10_3h | production_plus_market_context | separate_liquidity | 0.472222 | 0.253697 | -0.016506 | 0.309767 |  |
| exp_0012 | class_weight | ft_atr100_r10_3h | production_full | pooled | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |
| exp_0013 | class_weight | ft_atr100_r10_3h | production_full | pooled | 0.416667 | 0.241913 | -0.011053 | 0.590931 |  |
| exp_0014 | class_weight | ft_atr100_r10_3h | production_full | pooled | 0.359848 | 0.217830 | -0.005394 | 0.786447 |  |
| exp_0015 | tuning | ft_atr100_r10_3h | production_full | pooled | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |
| exp_0016 | tuning | ft_atr100_r10_3h | production_full | pooled | 0.391414 | 0.235555 | -0.000882 | 0.966414 |  |
| exp_0017 | seed_stability | ft_atr100_r10_3h | production_full | pooled | 0.409091 | 0.234440 | 0.002728 | 1.114228 |  |

The synthetic table is a control-flow/regression artifact only and must not be interpreted as market performance.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```
