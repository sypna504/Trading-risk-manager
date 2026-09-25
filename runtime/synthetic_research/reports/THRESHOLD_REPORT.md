# Threshold Report

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

{
  "global_best": {
    "threshold": 0.22000000000000003,
    "score": -0.7465512386763045,
    "trading": {
      "threshold": 0.22000000000000003,
      "trades": 15,
      "selected_rate": 0.45454545454545453,
      "win_rate": 0.2,
      "mean_net_return": -0.012001504507086019,
      "median_net_return": -0.01241028800774335,
      "total_net_return": -0.1800225676062903,
      "cumulative_return": -0.16744840681998896,
      "maximum_drawdown": -0.1667039810908929,
      "profit_factor": 0.10197771222065038,
      "average_win": 0.006814340743507103,
      "average_loss": -0.0167054658197343,
      "payoff_ratio": 0.4079108488826015,
      "sharpe_like": null,
      "by_month": {
        "2026-02": {
          "trades": 15,
          "mean_net_return": -0.012001504507086017,
          "total_net_return": -0.18002256760629026
        }
      },
      "by_symbol": {
        "ADAUSDT": {
          "trades": 7,
          "win_rate": 0.0,
          "mean_net_return": -0.019175359940007183,
          "total_net_return": -0.13422751958005028
        },
        "ETHUSDT": {
          "trades": 5,
          "win_rate": 0.2,
          "mean_net_return": -0.0089807358929173,
          "total_net_return": -0.044903679464586496
        },
        "SOLUSDT": {
          "trades": 3,
          "win_rate": 0.6666666666666666,
          "mean_net_return": -0.00029712285388449906,
          "total_net_return": -0.0008913685616534972
        }
      },
      "by_strategy": {
        "mean_reversion": {
          "trades": 15,
          "win_rate": 0.2,
          "mean_net_return": -0.012001504507086019,
          "total_net_return": -0.1800225676062903
        }
      },
      "by_interval": {
        "1h": {
          "trades": 15,
          "win_rate": 0.2,
          "mean_net_return": -0.012001504507086019,
          "total_net_return": -0.1800225676062903
        }
      },
      "by_trend_regime": {
        "down": {
          "trades": 11,
          "win_rate": 0.2727272727272727,
          "mean_net_return": -0.010806603499824064,
          "total_net_return": -0.1188726384980647
        },
        "range": {
          "trades": 4,
          "win_rate": 0.0,
          "mean_net_return": -0.015287482277056393,
          "total_net_return": -0.06114992910822557
        }
      },
      "by_volatility_regime": {
        "high": {
          "trades": 1,
          "win_rate": 0.0,
          "mean_net_return": -0.0020150431241975327,
          "total_net_return": -0.0020150431241975327
        },
        "low": {
          "trades": 14,
          "win_rate": 0.21428571428571427,
          "mean_net_return": -0.012714823177292339,
          "total_net_return": -0.17800752448209275
        }
      },
      "diagnostic_note": "trade-level aggregates are diagnostics, not a portfolio backtest; use portfolio_backtest for Sharpe, drawdown and portfolio return"
    },
    "portfolio": {
      "starting_capital": 10000.0,
      "ending_capital": 9630.665925055955,
      "portfolio_return": -0.036933407494404547,
      "trades": 13,
      "skipped_capacity": 2,
      "win_rate": 0.23076923076923078,
      "mean_trade_pnl": -28.41031345723426,
      "profit_factor": 0.11903539349457076,
      "maximum_drawdown": -0.04164304957792431,
      "sharpe": -27.366400899027347,
      "sortino": -18.451178242511652,
      "calmar": -23.98862292696362,
      "cagr": -0.9989594138536778,
      "turnover": 3.2172748164671314,
      "exposure": 0.24937247583912378,
      "average_holding_bars": 2.769230769230769,
      "cost_multiplier": 1.0,
      "base_round_trip_cost": 0.003,
      "max_concurrent_positions": 5,
      "max_portfolio_risk_pct": 5.0,
      "max_gross_exposure_pct": 100.0
    }
  },
  "global_portfolio": {
    "starting_capital": 10000.0,
    "ending_capital": 9630.665925055955,
    "portfolio_return": -0.036933407494404547,
    "trades": 13,
    "skipped_capacity": 2,
    "win_rate": 0.23076923076923078,
    "mean_trade_pnl": -28.41031345723426,
    "profit_factor": 0.11903539349457076,
    "maximum_drawdown": -0.04164304957792431,
    "sharpe": -27.366400899027347,
    "sortino": -18.451178242511652,
    "calmar": -23.98862292696362,
    "cagr": -0.9989594138536778,
    "turnover": 3.2172748164671314,
    "exposure": 0.24937247583912378,
    "average_holding_bars": 2.769230769230769,
    "cost_multiplier": 1.0,
    "base_round_trip_cost": 0.003,
    "max_concurrent_positions": 5,
    "max_portfolio_risk_pct": 5.0,
    "max_gross_exposure_pct": 100.0
  },
  "strategy_thresholds": {
    "breakout": {
      "threshold": 0.22000000000000003,
      "reason": "fallback to global"
    },
    "mean_reversion": {
      "threshold": 0.24000000000000002,
      "score": -0.7396941773577113,
      "trading": {
        "threshold": 0.24000000000000002,
        "trades": 10,
        "selected_rate": 0.3125,
        "win_rate": 0.2,
        "mean_net_return": -0.01351095472247402,
        "median_net_return": -0.01393216728561247,
        "total_net_return": -0.1351095472247402,
        "cumulative_return": -0.1281994829516927,
        "maximum_drawdown": -0.1291782492146738,
        "profit_factor": 0.008248168455551546,
        "average_win": 0.0005618372812720178,
        "average_loss": -0.017029152723410528,
        "payoff_ratio": 0.032992673822206185,
        "sharpe_like": null,
        "by_month": {
          "2026-02": {
            "trades": 10,
            "mean_net_return": -0.01351095472247402,
            "total_net_return": -0.1351095472247402
          }
        },
        "by_symbol": {
          "ADAUSDT": {
            "trades": 4,
            "win_rate": 0.0,
            "mean_net_return": -0.018002548663680114,
            "total_net_return": -0.07201019465472046
          },
          "ETHUSDT": {
            "trades": 4,
            "win_rate": 0.0,
            "mean_net_return": -0.016055756783140942,
            "total_net_return": -0.06422302713256377
          },
          "SOLUSDT": {
            "trades": 2,
            "win_rate": 1.0,
            "mean_net_return": 0.0005618372812720178,
            "total_net_return": 0.0011236745625440355
          }
        },
        "by_strategy": {
          "mean_reversion": {
            "trades": 10,
            "win_rate": 0.2,
            "mean_net_return": -0.01351095472247402,
            "total_net_return": -0.1351095472247402
          }
        },
        "by_interval": {
          "1h": {
            "trades": 10,
            "win_rate": 0.2,
            "mean_net_return": -0.01351095472247402,
            "total_net_return": -0.1351095472247402
          }
        },
        "by_trend_regime": {
          "down": {
            "trades": 6,
            "win_rate": 0.3333333333333333,
            "mean_net_return": -0.012326603019419104,
            "total_net_return": -0.07395961811651462
          },
          "range": {
            "trades": 4,
            "win_rate": 0.0,
            "mean_net_return": -0.015287482277056393,
            "total_net_return": -0.06114992910822557
          }
        },
        "by_volatility_regime": {
          "low": {
            "trades": 10,
            "win_rate": 0.2,
            "mean_net_return": -0.01351095472247402,
            "total_net_return": -0.1351095472247402
          }
        },
        "diagnostic_note": "trade-level aggregates are diagnostics, not a portfolio backtest; use portfolio_backtest for Sharpe, drawdown and portfolio return"
      },
      "portfolio": {
        "starting_capital": 10000.0,
        "ending_capital": 9680.662733865001,
        "portfolio_return": -0.0319337266134998,
        "trades": 9,
        "skipped_capacity": 1,
        "win_rate": 0.2222222222222222,
        "mean_trade_pnl": -35.48191845944406,
        "profit_factor": 0.00872021524433658,
        "maximum_drawdown": -0.03220559810129631,
        "sharpe": -32.40574139245113,
        "sortino": -20.648634698826843,
        "calmar": -31.047272979471018,
        "cagr": -0.99989599571808,
        "turnover": 2.2399311161072326,
        "exposure": 0.24948419565543378,
        "average_holding_bars": 2.7777777777777777,
        "cost_multiplier": 1.0,
        "base_round_trip_cost": 0.003,
        "max_concurrent_positions": 5,
        "max_portfolio_risk_pct": 5.0,
        "max_gross_exposure_pct": 100.0
      }
    }
  },
  "strategy_portfolio": {
    "starting_capital": 10000.0,
    "ending_capital": 9680.662733865001,
    "portfolio_return": -0.0319337266134998,
    "trades": 9,
    "skipped_capacity": 1,
    "win_rate": 0.2222222222222222,
    "mean_trade_pnl": -35.48191845944406,
    "profit_factor": 0.00872021524433658,
    "maximum_drawdown": -0.03220559810129631,
    "sharpe": -32.40574139245113,
    "sortino": -20.648634698826843,
    "calmar": -31.047272979471018,
    "cagr": -0.99989599571808,
    "turnover": 2.2399311161072326,
    "exposure": 0.24948419565543378,
    "average_holding_bars": 2.7777777777777777,
    "cost_multiplier": 1.0,
    "base_round_trip_cost": 0.003,
    "max_concurrent_positions": 5,
    "max_portfolio_risk_pct": 5.0,
    "max_gross_exposure_pct": 100.0
  },
  "selected": "strategy_specific"
}
