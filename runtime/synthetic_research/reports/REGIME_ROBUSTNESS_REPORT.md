# Regime Robustness Report

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

{
  "trading": {
    "threshold": {
      "__global__": 0.22000000000000003,
      "breakout": 0.22000000000000003,
      "mean_reversion": 0.24000000000000002
    },
    "trades": 88,
    "selected_rate": 0.3154121863799283,
    "win_rate": 0.375,
    "mean_net_return": -0.004956480931878709,
    "median_net_return": -0.004770654674217054,
    "total_net_return": -0.43617032200532635,
    "cumulative_return": -0.3587750238459465,
    "maximum_drawdown": -0.3607803416030173,
    "profit_factor": 0.40772842624977074,
    "average_win": 0.009098970853503089,
    "average_loss": -0.013389752003107786,
    "payoff_ratio": 0.6795473770829513,
    "sharpe_like": null,
    "by_month": {
      "2026-02": {
        "trades": 86,
        "mean_net_return": -0.0050114986367845865,
        "total_net_return": -0.4309888827634744
      },
      "2026-03": {
        "trades": 2,
        "mean_net_return": -0.002590719620925938,
        "total_net_return": -0.005181439241851876
      }
    },
    "by_symbol": {
      "ADAUSDT": {
        "trades": 15,
        "win_rate": 0.6,
        "mean_net_return": 0.001996741458609237,
        "total_net_return": 0.029951121879138558
      },
      "BTCUSDT": {
        "trades": 17,
        "win_rate": 0.4117647058823529,
        "mean_net_return": -0.0010905794670190735,
        "total_net_return": -0.01853985093932425
      },
      "ETHUSDT": {
        "trades": 38,
        "win_rate": 0.3684210526315789,
        "mean_net_return": -0.005812700006990117,
        "total_net_return": -0.22088260026562445
      },
      "SOLUSDT": {
        "trades": 18,
        "win_rate": 0.16666666666666666,
        "mean_net_return": -0.012594388482195342,
        "total_net_return": -0.22669899267951615
      }
    },
    "by_strategy": {
      "breakout": {
        "trades": 6,
        "win_rate": 0.5,
        "mean_net_return": -0.002891406478461604,
        "total_net_return": -0.017348438870769624
      },
      "mean_reversion": {
        "trades": 82,
        "win_rate": 0.36585365853658536,
        "mean_net_return": -0.005107583940665327,
        "total_net_return": -0.41882188313455676
      }
    },
    "by_interval": {
      "1h": {
        "trades": 88,
        "win_rate": 0.375,
        "mean_net_return": -0.004956480931878709,
        "total_net_return": -0.43617032200532635
      }
    },
    "by_trend_regime": {
      "down": {
        "trades": 71,
        "win_rate": 0.39436619718309857,
        "mean_net_return": -0.004390307660993202,
        "total_net_return": -0.3117118439305174
      },
      "range": {
        "trades": 12,
        "win_rate": 0.16666666666666666,
        "mean_net_return": -0.010042983028083928,
        "total_net_return": -0.12051579633700713
      },
      "up": {
        "trades": 5,
        "win_rate": 0.6,
        "mean_net_return": -0.0007885363475603722,
        "total_net_return": -0.003942681737801861
      }
    },
    "by_volatility_regime": {
      "high": {
        "trades": 30,
        "win_rate": 0.4666666666666667,
        "mean_net_return": -0.002571611934100157,
        "total_net_return": -0.07714835802300471
      },
      "low": {
        "trades": 58,
        "win_rate": 0.3275862068965517,
        "mean_net_return": -0.006190033861764165,
        "total_net_return": -0.3590219639823216
      }
    },
    "diagnostic_note": "trade-level aggregates are diagnostics, not a portfolio backtest; use portfolio_backtest for Sharpe, drawdown and portfolio return"
  },
  "concentration": {
    "trades": 88,
    "top_symbol_pnl_share": 0.09974861646730755,
    "top_month_pnl_share": 0.0,
    "top_strategy_trade_share": 0.9318181818181818,
    "by_symbol": {
      "ADAUSDT": {
        "count": 15,
        "mean": 0.001996741458609237,
        "sum": 0.029951121879138558
      },
      "BTCUSDT": {
        "count": 17,
        "mean": -0.0010905794670190737,
        "sum": -0.018539850939324254
      },
      "ETHUSDT": {
        "count": 38,
        "mean": -0.005812700006990117,
        "sum": -0.22088260026562445
      },
      "SOLUSDT": {
        "count": 18,
        "mean": -0.012594388482195342,
        "sum": -0.22669899267951615
      }
    },
    "by_month": {
      "2026-02": {
        "count": 86,
        "mean": -0.0050114986367845865,
        "sum": -0.4309888827634744
      },
      "2026-03": {
        "count": 2,
        "mean": -0.002590719620925938,
        "sum": -0.005181439241851876
      }
    },
    "by_strategy": {
      "breakout": {
        "count": 6,
        "mean": -0.0028914064784616045,
        "sum": -0.017348438870769627
      },
      "mean_reversion": {
        "count": 82,
        "mean": -0.005107583940665325,
        "sum": -0.41882188313455665
      }
    }
  }
}
