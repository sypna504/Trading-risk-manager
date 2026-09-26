# Walk Forward Report

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

{
  "folds": [
    {
      "fold": 0,
      "train_start": "2026-01-03 04:00:00",
      "train_end": "2026-01-18 14:00:00",
      "test_start": "2026-01-23 06:00:00",
      "test_end": "2026-01-26 14:00:00",
      "thresholds": {
        "__global__": 0.1
      },
      "metrics": {
        "classification": {
          "positive_class_rate": 0.15254237288135594,
          "precision": 0.15254237288135594,
          "recall": 1.0,
          "f1": 0.2647058823529412,
          "confusion_matrix": [
            [
              0,
              50
            ],
            [
              0,
              9
            ]
          ],
          "roc_auc": 0.4633333333333333,
          "pr_auc": 0.17850614822200067,
          "log_loss": 0.6550390698235233,
          "brier_score": 0.23099146317462377,
          "single_class_test": false
        },
        "probabilities": {
          "count": 59,
          "unique_count": 9,
          "min": 0.43933356400209217,
          "max": 0.5256378778839954,
          "mean": 0.46786635402988414,
          "std": 0.02085698801955899,
          "range": 0.08630431388190324,
          "q05": 0.43933356400209217,
          "q25": 0.45932275684154233,
          "median": 0.4716375678244981,
          "q75": 0.4728745421868624,
          "q95": 0.5256378778839954,
          "expected_calibration_error": 0.31532398114852817,
          "calibration_curve": [
            {
              "left": 0.4,
              "right": 0.5,
              "count": 54,
              "mean_probability": 0.46257483598282867,
              "positive_rate": 0.16666666666666666
            },
            {
              "left": 0.5,
              "right": 0.6000000000000001,
              "count": 5,
              "mean_probability": 0.5250147489380824,
              "positive_rate": 0.0
            }
          ]
        },
        "trading": {
          "threshold": {
            "__global__": 0.1
          },
          "trades": 59,
          "selected_rate": 1.0,
          "win_rate": 0.3050847457627119,
          "mean_net_return": -0.005205418378251366,
          "median_net_return": -0.00522834996716248,
          "total_net_return": -0.30711968431683057,
          "cumulative_return": -0.26875224037001,
          "maximum_drawdown": -0.26107497084442477,
          "profit_factor": 0.40626497595293215,
          "average_win": 0.011674864872395975,
          "average_loss": -0.012616274439511172,
          "payoff_ratio": 0.9253813341150121,
          "sharpe_like": null,
          "by_month": {
            "2026-01": {
              "trades": 59,
              "mean_net_return": -0.005205418378251365,
              "total_net_return": -0.3071196843168305
            }
          },
          "by_symbol": {
            "ADAUSDT": {
              "trades": 3,
              "win_rate": 1.0,
              "mean_net_return": 0.004752368965985005,
              "total_net_return": 0.014257106897955016
            },
            "BTCUSDT": {
              "trades": 15,
              "win_rate": 0.2,
              "mean_net_return": -0.008974223217317,
              "total_net_return": -0.134613348259755
            },
            "ETHUSDT": {
              "trades": 9,
              "win_rate": 0.3333333333333333,
              "mean_net_return": -0.0017926407420166541,
              "total_net_return": -0.016133766678149888
            },
            "SOLUSDT": {
              "trades": 32,
              "win_rate": 0.28125,
              "mean_net_return": -0.00533217738365252,
              "total_net_return": -0.17062967627688064
            }
          },
          "by_strategy": {
            "breakout": {
              "trades": 3,
              "win_rate": 0.6666666666666666,
              "mean_net_return": 0.009243159114701345,
              "total_net_return": 0.027729477344104036
            },
            "mean_reversion": {
              "trades": 56,
              "win_rate": 0.2857142857142857,
              "mean_net_return": -0.005979449315373831,
              "total_net_return": -0.33484916166093454
            }
          },
          "by_interval": {
            "1h": {
              "trades": 59,
              "win_rate": 0.3050847457627119,
              "mean_net_return": -0.005205418378251366,
              "total_net_return": -0.30711968431683057
            }
          },
          "by_trend_regime": {
            "down": {
              "trades": 54,
              "win_rate": 0.2962962962962963,
              "mean_net_return": -0.005309101814715533,
              "total_net_return": -0.2866914979946388
            },
            "range": {
              "trades": 2,
              "win_rate": 0.0,
              "mean_net_return": -0.024078831833147903,
              "total_net_return": -0.04815766366629581
            },
            "up": {
              "trades": 3,
              "win_rate": 0.6666666666666666,
              "mean_net_return": 0.009243159114701345,
              "total_net_return": 0.027729477344104036
            }
          },
          "by_volatility_regime": {
            "high": {
              "trades": 20,
              "win_rate": 0.35,
              "mean_net_return": -0.004116158574654974,
              "total_net_return": -0.08232317149309948
            },
            "low": {
              "trades": 39,
              "win_rate": 0.28205128205128205,
              "mean_net_return": -0.005764013149326437,
              "total_net_return": -0.22479651282373103
            }
          },
          "diagnostic_note": "trade-level aggregates are diagnostics, not a portfolio backtest; use portfolio_backtest for Sharpe, drawdown and portfolio return"
        },
        "model": {},
        "raw_probability_diagnostics": {
          "positive_rate_baseline": 0.15254237288135594,
          "top_buckets": {
            "top_1pct": {
              "observations": 1,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.015200624800426162,
              "total_net_return": -0.015200624800426162,
              "profit_factor": 0.0
            },
            "top_2pct": {
              "observations": 2,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.01947232309657659,
              "total_net_return": -0.03894464619315318,
              "profit_factor": 0.0
            },
            "top_5pct": {
              "observations": 3,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.016001468850012888,
              "total_net_return": -0.04800440655003867,
              "profit_factor": 0.0
            },
            "top_10pct": {
              "observations": 6,
              "positive_rate": 0.16666666666666666,
              "lift_over_baseline": 1.0925925925925926,
              "mean_net_return": -0.005767237762219432,
              "total_net_return": -0.034603426573316595,
              "profit_factor": 0.38372971569906605
            },
            "top_20pct": {
              "observations": 12,
              "positive_rate": 0.25,
              "lift_over_baseline": 1.6388888888888888,
              "mean_net_return": -0.0028940764118964997,
              "total_net_return": -0.034728916942757995,
              "profit_factor": 0.674997472311265
            }
          }
        },
        "probability_rank_diagnostics": {
          "positive_rate_baseline": 0.15254237288135594,
          "top_buckets": {
            "top_1pct": {
              "observations": 1,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.015200624800426162,
              "total_net_return": -0.015200624800426162,
              "profit_factor": 0.0
            },
            "top_2pct": {
              "observations": 2,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.01947232309657659,
              "total_net_return": -0.03894464619315318,
              "profit_factor": 0.0
            },
            "top_5pct": {
              "observations": 3,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.016001468850012888,
              "total_net_return": -0.04800440655003867,
              "profit_factor": 0.0
            },
            "top_10pct": {
              "observations": 6,
              "positive_rate": 0.16666666666666666,
              "lift_over_baseline": 1.0925925925925926,
              "mean_net_return": -0.005767237762219432,
              "total_net_return": -0.034603426573316595,
              "profit_factor": 0.38372971569906605
            },
            "top_20pct": {
              "observations": 12,
              "positive_rate": 0.25,
              "lift_over_baseline": 1.6388888888888888,
              "mean_net_return": -0.0028940764118964997,
              "total_net_return": -0.034728916942757995,
              "profit_factor": 0.674997472311265
            }
          }
        },
        "expected_utility": {
          "reference": {
            "__global__": {
              "expected_win": 0.019775880459937646,
              "expected_loss": -0.007895075055085722,
              "rows": 22
            },
            "breakout": {
              "expected_win": 0.019708994094944757,
              "expected_loss": -0.00043673042232844324,
              "rows": 3
            },
            "mean_reversion": {
              "expected_win": 0.01978702818743646,
              "expected_loss": -0.009042512690894535,
              "rows": 19
            }
          },
          "valid_rows": 59,
          "selected_rows": 59,
          "mean_expected_utility": 0.004674643890700406,
          "mean_realized_net_return": -0.005205418378251366,
          "total_realized_net_return": -0.30711968431683057,
          "profit_factor": 0.40626497595293215,
          "portfolio": {
            "starting_capital": 10000.0,
            "ending_capital": 9190.806809278287,
            "portfolio_return": -0.08091931907217131,
            "trades": 54,
            "skipped_capacity": 5,
            "win_rate": 0.25925925925925924,
            "mean_trade_pnl": -14.985059087439097,
            "profit_factor": 0.3133870952069451,
            "maximum_drawdown": -0.08319309836530542,
            "sharpe": -27.372828538155193,
            "sortino": -27.101409995310192,
            "calmar": -12.018415614888973,
            "cagr": -0.9998492324445809,
            "turnover": 12.936965464204793,
            "exposure": 0.24993629728213776,
            "average_holding_bars": 2.740740740740741,
            "cost_multiplier": 1.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          }
        },
        "portfolio": {
          "cost_1x": {
            "starting_capital": 10000.0,
            "ending_capital": 9190.806809278287,
            "portfolio_return": -0.08091931907217131,
            "trades": 54,
            "skipped_capacity": 5,
            "win_rate": 0.25925925925925924,
            "mean_trade_pnl": -14.985059087439097,
            "profit_factor": 0.3133870952069451,
            "maximum_drawdown": -0.08319309836530542,
            "sharpe": -27.372828538155193,
            "sortino": -27.101409995310192,
            "calmar": -12.018415614888973,
            "cagr": -0.9998492324445809,
            "turnover": 12.936965464204793,
            "exposure": 0.24993629728213776,
            "average_holding_bars": 2.740740740740741,
            "cost_multiplier": 1.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "cost_1_5x": {
            "starting_capital": 10000.0,
            "ending_capital": 9005.140392160014,
            "portfolio_return": -0.09948596078399863,
            "trades": 54,
            "skipped_capacity": 5,
            "win_rate": 0.25925925925925924,
            "mean_trade_pnl": -18.42332607111095,
            "profit_factor": 0.24090656572328428,
            "maximum_drawdown": -0.10025204046758718,
            "sharpe": -33.03732141701173,
            "sortino": -32.31447471145362,
            "calmar": -9.974680292469492,
            "cagr": -0.9999820523318959,
            "turnover": 12.817434603004397,
            "exposure": 0.24992287088226592,
            "average_holding_bars": 2.740740740740741,
            "cost_multiplier": 1.5,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "cost_2x": {
            "starting_capital": 10000.0,
            "ending_capital": 8822.985820469581,
            "portfolio_return": -0.1177014179530419,
            "trades": 54,
            "skipped_capacity": 5,
            "win_rate": 0.2037037037037037,
            "mean_trade_pnl": -21.796558880192965,
            "profit_factor": 0.1881561306501486,
            "maximum_drawdown": -0.11777330913705486,
            "sharpe": -38.18323460595038,
            "sortino": -36.66237839845258,
            "calmar": -8.490870103121527,
            "cagr": -0.9999978694975084,
            "turnover": 12.699146025246558,
            "exposure": 0.24990579043587893,
            "average_holding_bars": 2.740740740740741,
            "cost_multiplier": 2.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "cost_3x": {
            "starting_capital": 10000.0,
            "ending_capital": 8468.86641159326,
            "portfolio_return": -0.1531133588406739,
            "trades": 54,
            "skipped_capacity": 5,
            "win_rate": 0.16666666666666666,
            "mean_trade_pnl": -28.354325711236,
            "profit_factor": 0.11544671781021036,
            "maximum_drawdown": -0.1531133588406739,
            "sharpe": -46.89932609753687,
            "sortino": -44.82469964081029,
            "calmar": -6.531108571066479,
            "cagr": -0.9999999702691028,
            "turnover": 12.466580419291137,
            "exposure": 0.24987022036749607,
            "average_holding_bars": 2.740740740740741,
            "cost_multiplier": 3.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "all_signals": {
            "starting_capital": 10000.0,
            "ending_capital": 9190.806809278287,
            "portfolio_return": -0.08091931907217131,
            "trades": 54,
            "skipped_capacity": 5,
            "win_rate": 0.25925925925925924,
            "mean_trade_pnl": -14.985059087439097,
            "profit_factor": 0.3133870952069451,
            "maximum_drawdown": -0.08319309836530542,
            "sharpe": -27.372828538155193,
            "sortino": -27.101409995310192,
            "calmar": -12.018415614888973,
            "cagr": -0.9998492324445809,
            "turnover": 12.936965464204793,
            "exposure": 0.24993629728213776,
            "average_holding_bars": 2.740740740740741,
            "cost_multiplier": 1.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          }
        }
      }
    },
    {
      "fold": 1,
      "train_start": "2026-01-03 04:00:00",
      "train_end": "2026-01-26 10:00:00",
      "test_start": "2026-02-04 10:00:00",
      "test_end": "2026-02-09 14:00:00",
      "thresholds": {
        "__global__": 0.1
      },
      "metrics": {
        "classification": {
          "positive_class_rate": 0.18840579710144928,
          "precision": 0.16071428571428573,
          "recall": 0.6923076923076923,
          "f1": 0.2608695652173913,
          "confusion_matrix": [
            [
              9,
              47
            ],
            [
              4,
              9
            ]
          ],
          "roc_auc": 0.3461538461538462,
          "pr_auc": 0.15077404207733008,
          "log_loss": 0.5773021460779635,
          "brier_score": 0.18220084612097753,
          "single_class_test": false
        },
        "probabilities": {
          "count": 69,
          "unique_count": 69,
          "min": 0.0611789035345229,
          "max": 0.492702887818047,
          "mean": 0.21771838871256613,
          "std": 0.10602401723306752,
          "range": 0.4315239842835241,
          "q05": 0.07881950882903672,
          "q25": 0.11529132054201256,
          "median": 0.21866497131105175,
          "q75": 0.2927797093653149,
          "q95": 0.3792582173502352,
          "expected_calibration_error": 0.1563296483457424,
          "calibration_curve": [
            {
              "left": 0.0,
              "right": 0.1,
              "count": 13,
              "mean_probability": 0.084160296371158,
              "positive_rate": 0.3076923076923077
            },
            {
              "left": 0.1,
              "right": 0.2,
              "count": 18,
              "mean_probability": 0.1402126494350202,
              "positive_rate": 0.2222222222222222
            },
            {
              "left": 0.2,
              "right": 0.30000000000000004,
              "count": 21,
              "mean_probability": 0.254730329230192,
              "positive_rate": 0.19047619047619047
            },
            {
              "left": 0.30000000000000004,
              "right": 0.4,
              "count": 14,
              "mean_probability": 0.3351124101218409,
              "positive_rate": 0.07142857142857142
            },
            {
              "left": 0.4,
              "right": 0.5,
              "count": 3,
              "mean_probability": 0.4545822076572794,
              "positive_rate": 0.0
            }
          ]
        },
        "trading": {
          "threshold": {
            "__global__": 0.1
          },
          "trades": 56,
          "selected_rate": 0.8115942028985508,
          "win_rate": 0.39285714285714285,
          "mean_net_return": -0.00538706179028312,
          "median_net_return": -0.005475388312747351,
          "total_net_return": -0.3016754602558547,
          "cumulative_return": -0.2663473120720178,
          "maximum_drawdown": -0.3018696663755631,
          "profit_factor": 0.4339765951476468,
          "average_win": 0.01051354606373127,
          "average_loss": -0.015675690401704193,
          "payoff_ratio": 0.6706911015918178,
          "sharpe_like": null,
          "by_month": {
            "2026-02": {
              "trades": 56,
              "mean_net_return": -0.005387061790283118,
              "total_net_return": -0.3016754602558546
            }
          },
          "by_symbol": {
            "ADAUSDT": {
              "trades": 21,
              "win_rate": 0.23809523809523808,
              "mean_net_return": -0.012386735867821227,
              "total_net_return": -0.2601214532242458
            },
            "BTCUSDT": {
              "trades": 13,
              "win_rate": 0.38461538461538464,
              "mean_net_return": -0.0049803096613519875,
              "total_net_return": -0.06474402559757583
            },
            "ETHUSDT": {
              "trades": 13,
              "win_rate": 0.6153846153846154,
              "mean_net_return": 0.0014769644707116733,
              "total_net_return": 0.019200538119251754
            },
            "SOLUSDT": {
              "trades": 9,
              "win_rate": 0.4444444444444444,
              "mean_net_return": 0.00044327560519058235,
              "total_net_return": 0.003989480446715241
            }
          },
          "by_strategy": {
            "breakout": {
              "trades": 7,
              "win_rate": 0.2857142857142857,
              "mean_net_return": -0.008501640473764194,
              "total_net_return": -0.05951148331634935
            },
            "mean_reversion": {
              "trades": 49,
              "win_rate": 0.40816326530612246,
              "mean_net_return": -0.004942121978357251,
              "total_net_return": -0.2421639769395053
            }
          },
          "by_interval": {
            "1h": {
              "trades": 56,
              "win_rate": 0.39285714285714285,
              "mean_net_return": -0.00538706179028312,
              "total_net_return": -0.3016754602558547
            }
          },
          "by_trend_regime": {
            "down": {
              "trades": 42,
              "win_rate": 0.4523809523809524,
              "mean_net_return": -0.0028094647733296063,
              "total_net_return": -0.11799752047984347
            },
            "range": {
              "trades": 8,
              "win_rate": 0.125,
              "mean_net_return": -0.018649605125342996,
              "total_net_return": -0.14919684100274397
            },
            "up": {
              "trades": 6,
              "win_rate": 0.3333333333333333,
              "mean_net_return": -0.005746849795544534,
              "total_net_return": -0.0344810987732672
            }
          },
          "by_volatility_regime": {
            "high": {
              "trades": 18,
              "win_rate": 0.5,
              "mean_net_return": 0.003119301677118118,
              "total_net_return": 0.056147430188126124
            },
            "low": {
              "trades": 38,
              "win_rate": 0.34210526315789475,
              "mean_net_return": -0.009416391853788966,
              "total_net_return": -0.35782289044398075
            }
          },
          "diagnostic_note": "trade-level aggregates are diagnostics, not a portfolio backtest; use portfolio_backtest for Sharpe, drawdown and portfolio return"
        },
        "model": {},
        "raw_probability_diagnostics": {
          "positive_rate_baseline": 0.18840579710144928,
          "top_buckets": {
            "top_1pct": {
              "observations": 1,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.022167685281911816,
              "total_net_return": -0.022167685281911816,
              "profit_factor": 0.0
            },
            "top_2pct": {
              "observations": 2,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.011695674583001688,
              "total_net_return": -0.023391349166003376,
              "profit_factor": 0.0
            },
            "top_5pct": {
              "observations": 4,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.0068526456712344995,
              "total_net_return": -0.027410582684937998,
              "profit_factor": 0.04660153066391101
            },
            "top_10pct": {
              "observations": 7,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.006978154794988674,
              "total_net_return": -0.04884708356492072,
              "profit_factor": 0.1701020095415941
            },
            "top_20pct": {
              "observations": 14,
              "positive_rate": 0.07142857142857142,
              "lift_over_baseline": 0.3791208791208791,
              "mean_net_return": -0.007619705095120394,
              "total_net_return": -0.10667587133168552,
              "profit_factor": 0.2237189223837923
            }
          }
        },
        "probability_rank_diagnostics": {
          "positive_rate_baseline": 0.18840579710144928,
          "top_buckets": {
            "top_1pct": {
              "observations": 1,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.022167685281911816,
              "total_net_return": -0.022167685281911816,
              "profit_factor": 0.0
            },
            "top_2pct": {
              "observations": 2,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.011695674583001688,
              "total_net_return": -0.023391349166003376,
              "profit_factor": 0.0
            },
            "top_5pct": {
              "observations": 4,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.0068526456712344995,
              "total_net_return": -0.027410582684937998,
              "profit_factor": 0.04660153066391101
            },
            "top_10pct": {
              "observations": 7,
              "positive_rate": 0.0,
              "lift_over_baseline": 0.0,
              "mean_net_return": -0.006978154794988674,
              "total_net_return": -0.04884708356492072,
              "profit_factor": 0.1701020095415941
            },
            "top_20pct": {
              "observations": 14,
              "positive_rate": 0.07142857142857142,
              "lift_over_baseline": 0.3791208791208791,
              "mean_net_return": -0.007619705095120394,
              "total_net_return": -0.10667587133168552,
              "profit_factor": 0.2237189223837923
            }
          }
        },
        "expected_utility": {
          "reference": {
            "__global__": {
              "expected_win": 0.01780785466481383,
              "expected_loss": -0.0031111793544534843,
              "rows": 21
            },
            "breakout": {
              "expected_win": 0.017761616457509514,
              "expected_loss": -0.0051419200178694285,
              "rows": 5
            },
            "mean_reversion": {
              "expected_win": 0.01783097376846599,
              "expected_loss": -0.0026034941885994963,
              "rows": 16
            }
          },
          "valid_rows": 69,
          "selected_rows": 46,
          "mean_expected_utility": 0.001628823861927068,
          "mean_realized_net_return": -0.00583347286112971,
          "total_realized_net_return": -0.26833975161196666,
          "profit_factor": 0.40277806903055163,
          "portfolio": {
            "starting_capital": 10000.0,
            "ending_capital": 9365.159248360937,
            "portfolio_return": -0.0634840751639063,
            "trades": 42,
            "skipped_capacity": 4,
            "win_rate": 0.3333333333333333,
            "mean_trade_pnl": -15.115255991406176,
            "profit_factor": 0.36807652379776007,
            "maximum_drawdown": -0.07834195265913169,
            "sharpe": -18.71250946136863,
            "sortino": -13.726273166759071,
            "calmar": -12.626124583206773,
            "cagr": -0.9891552543658838,
            "turnover": 9.904549802026384,
            "exposure": 0.24961683695441478,
            "average_holding_bars": 2.738095238095238,
            "cost_multiplier": 1.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          }
        },
        "portfolio": {
          "cost_1x": {
            "starting_capital": 10000.0,
            "ending_capital": 9287.383871653836,
            "portfolio_return": -0.0712616128346164,
            "trades": 52,
            "skipped_capacity": 4,
            "win_rate": 0.38461538461538464,
            "mean_trade_pnl": -13.704156314349108,
            "profit_factor": 0.40467393181773276,
            "maximum_drawdown": -0.08365175737518149,
            "sharpe": -19.124675092565084,
            "sortino": -14.085019056647505,
            "calmar": -11.88138786993966,
            "cagr": -0.9938989753766169,
            "turnover": 12.18997360789547,
            "exposure": 0.24966445330378392,
            "average_holding_bars": 2.6923076923076925,
            "cost_multiplier": 1.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "cost_1_5x": {
            "starting_capital": 10000.0,
            "ending_capital": 9107.181122836662,
            "portfolio_return": -0.08928188771633372,
            "trades": 52,
            "skipped_capacity": 4,
            "win_rate": 0.34615384615384615,
            "mean_trade_pnl": -17.169593791602654,
            "profit_factor": 0.3153426705672766,
            "maximum_drawdown": -0.09815209195291374,
            "sharpe": -23.124589551883567,
            "sortino": -16.507469066463223,
            "calmar": -10.172179931690122,
            "cagr": -0.9984207400168327,
            "turnover": 12.080663039865891,
            "exposure": 0.24963405785095755,
            "average_holding_bars": 2.6923076923076925,
            "cost_multiplier": 1.5,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "cost_2x": {
            "starting_capital": 10000.0,
            "ending_capital": 8930.160317139073,
            "portfolio_return": -0.1069839682860928,
            "trades": 52,
            "skipped_capacity": 4,
            "win_rate": 0.2692307692307692,
            "mean_trade_pnl": -20.573840055017897,
            "profit_factor": 0.24727064017465117,
            "maximum_drawdown": -0.11502568862786589,
            "sharpe": -26.62831301182048,
            "sortino": -18.60930708799952,
            "calmar": -8.690164865279412,
            "cagr": -0.9995921979184497,
            "turnover": 11.97250424208407,
            "exposure": 0.2496022501376047,
            "average_holding_bars": 2.6923076923076925,
            "cost_multiplier": 2.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "cost_3x": {
            "starting_capital": 10000.0,
            "ending_capital": 8585.661210800787,
            "portfolio_return": -0.14143387891992132,
            "trades": 52,
            "skipped_capacity": 4,
            "win_rate": 0.25,
            "mean_trade_pnl": -27.1988228692155,
            "profit_factor": 0.15149982539083917,
            "maximum_drawdown": -0.14789961139129226,
            "sharpe": -32.292003503029605,
            "sortino": -23.15718107199254,
            "calmar": -6.761160181139882,
            "cagr": -0.9999729633448677,
            "turnover": 11.759782288603047,
            "exposure": 0.2495380860336101,
            "average_holding_bars": 2.6923076923076925,
            "cost_multiplier": 3.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          },
          "all_signals": {
            "starting_capital": 10000.0,
            "ending_capital": 9433.36283223826,
            "portfolio_return": -0.0566637167761741,
            "trades": 61,
            "skipped_capacity": 8,
            "win_rate": 0.4426229508196721,
            "mean_trade_pnl": -9.28913389773331,
            "profit_factor": 0.5526190975642554,
            "maximum_drawdown": -0.07896097926478163,
            "sharpe": -14.052793137149504,
            "sortino": -11.086211573080096,
            "calmar": -12.437926467489063,
            "cagr": -0.9821108538962826,
            "turnover": 14.112267775657443,
            "exposure": 0.24524206557178913,
            "average_holding_bars": 2.7049180327868854,
            "cost_multiplier": 1.0,
            "base_round_trip_cost": 0.003,
            "max_concurrent_positions": 5,
            "max_portfolio_risk_pct": 5.0,
            "max_gross_exposure_pct": 100.0
          }
        }
      }
    }
  ],
  "completed_folds": 2,
  "positive_return_fold_rate": 0.0,
  "median_portfolio_return": -0.07609046595339386,
  "worst_portfolio_return": -0.08091931907217131
}
