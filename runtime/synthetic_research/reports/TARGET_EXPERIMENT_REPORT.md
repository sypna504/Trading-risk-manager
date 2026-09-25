# Target Experiment Report

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

Selected target: **ft_atr100_r10_3h**

```csv
experiment_id,phase,target,feature_set,architecture,class_weight,parameters,seed,roc_auc,pr_auc,pr_baseline,brier,trades,profit_factor,portfolio_return,max_drawdown,cost_1_5x,cost_2x,score,error
exp_0001,target,ft_atr100_r10_3h,production_full,pooled,none,synthetic_d4,42,0.40909090909090906,0.23443999957157852,0.26666666666666666,0.22806932333118707,18,1.1142281009129382,0.00272768777100163,-0.017470108391387518,-0.004014326162809612,-0.010719617398787573,-0.014446535121950509,
exp_0002,target,ft_atr100_r10_3h,production_full,pooled,balanced,synthetic_d4,42,0.4166666666666666,0.24191250408017123,0.26666666666666666,0.2559185882628428,17,0.5909311285387319,-0.011053120204675415,-0.018160864966139,-0.016991228877936915,-0.02290173102790538,-0.3025331790706053,
```

```json
{
  "ft_atr100_r10_3h": {
    "rows": 720,
    "positive_class_rate": 0.16944444444444445,
    "net_return_mean": -0.0024524171035553415,
    "net_return_median": -0.0024404959226876884,
    "exit_reason": {
      "timeout": 487,
      "take_profit": 122,
      "stop_loss": 111
    },
    "by_month": {
      "2026-01": {
        "rows": 350,
        "positive_rate": 0.18857142857142858,
        "mean_net_return": -0.001387552136742323,
        "median_net_return": -0.001777089546581287
      },
      "2026-02": {
        "rows": 368,
        "positive_rate": 0.15217391304347827,
        "mean_net_return": -0.003464444639832013,
        "median_net_return": -0.0033354335817039034
      },
      "2026-03": {
        "rows": 2,
        "positive_rate": 0.0,
        "mean_net_return": -0.002590719620925938,
        "median_net_return": -0.002590719620925938
      }
    },
    "by_symbol": {
      "ADAUSDT": {
        "rows": 180,
        "positive_rate": 0.17777777777777778,
        "mean_net_return": -0.001552847751241466,
        "median_net_return": -0.0015020445271441947
      },
      "BTCUSDT": {
        "rows": 142,
        "positive_rate": 0.19014084507042253,
        "mean_net_return": -0.001083363828269759,
        "median_net_return": -0.0018135344480795209
      },
      "ETHUSDT": {
        "rows": 185,
        "positive_rate": 0.11351351351351352,
        "mean_net_return": -0.0044559842317679,
        "median_net_return": -0.00484106038403653
      },
      "SOLUSDT": {
        "rows": 213,
        "positive_rate": 0.19718309859154928,
        "mean_net_return": -0.0023851313279108664,
        "median_net_return": -0.003193896802884175
      }
    },
    "by_strategy": {
      "breakout": {
        "rows": 65,
        "positive_rate": 0.16923076923076924,
        "mean_net_return": -0.0033609665984390613,
        "median_net_return": -0.005274158322720932
      },
      "mean_reversion": {
        "rows": 655,
        "positive_rate": 0.16946564885496182,
        "mean_net_return": -0.0023622557032997047,
        "median_net_return": -0.002327667772927253
      }
    },
    "by_trend_regime": {
      "down": {
        "rows": 600,
        "positive_rate": 0.16333333333333333,
        "mean_net_return": -0.002245332806839563,
        "median_net_return": -0.002131621743056142
      },
      "range": {
        "rows": 58,
        "positive_rate": 0.22413793103448276,
        "mean_net_return": -0.004290316711552302,
        "median_net_return": -0.005347383704973949
      },
      "up": {
        "rows": 62,
        "positive_rate": 0.1774193548387097,
        "mean_net_return": -0.0027371332449366787,
        "median_net_return": -0.004361414766421043
      }
    },
    "by_volatility_regime": {
      "high": {
        "rows": 269,
        "positive_rate": 0.17843866171003717,
        "mean_net_return": 0.00038266270293310547,
        "median_net_return": -0.00037406947501683347
      },
      "low": {
        "rows": 451,
        "positive_rate": 0.164079822616408,
        "mean_net_return": -0.004143407054653772,
        "median_net_return": -0.0036616348211346824
      }
    }
  }
}
```
