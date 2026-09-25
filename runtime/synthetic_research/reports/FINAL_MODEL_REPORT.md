# Final Model Report

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

```json
{
  "best_target": {
    "name": "ft_atr100_r10_3h",
    "definition": "first_touch_atr_rr",
    "horizon_minutes": 180,
    "atr_stop_multiplier": 1.0,
    "reward_ratio": 1.0,
    "minimum_net_return": 0.002,
    "maximum_drawdown": -0.015
  },
  "best_feature_set": "production_full",
  "best_research_feature_set": "production_full",
  "best_architecture_research": "pooled",
  "regression_research": {
    "status": "completed",
    "selection": {
      "threshold_selection": {
        "threshold": -9.457308140196593e-05,
        "score": null,
        "reason": "no threshold met minimum trade count"
      },
      "candidates": []
    },
    "metrics": {
      "regression": {
        "rmse": 0.013971741531554649,
        "mae": 0.011559225418498374,
        "correlation": -0.2485620397305074,
        "prediction_mean": -0.0008391371215660624,
        "prediction_std": 0.0009361356657539739
      },
      "trading": {
        "trades": 7,
        "selected_rate": 0.15555555555555556,
        "mean_net_return": -0.005924373412721798,
        "total_net_return": -0.041470613889052585,
        "profit_factor": 0.32195183238820746
      },
      "portfolio": {
        "cost_1x": {
          "starting_capital": 10000.0,
          "ending_capital": 9896.243032939816,
          "portfolio_return": -0.010375696706018456,
          "trades": 7,
          "skipped_capacity": 0,
          "win_rate": 0.14285714285714285,
          "mean_trade_pnl": -14.822423865740896,
          "profit_factor": 0.3192577209101568,
          "maximum_drawdown": -0.012908104155788691,
          "sharpe": -10.300122859307077,
          "sortino": -3.1782979497037944,
          "calmar": -46.40077212903784,
          "cagr": -0.5989459995506374,
          "turnover": 1.7396762953168476,
          "exposure": 0.25,
          "average_holding_bars": 2.857142857142857,
          "cost_multiplier": 1.0,
          "base_round_trip_cost": 0.003,
          "max_concurrent_positions": 5,
          "max_portfolio_risk_pct": 5.0,
          "max_gross_exposure_pct": 100.0
        },
        "cost_1_5x": {
          "starting_capital": 10000.0,
          "ending_capital": 9870.186806812833,
          "portfolio_return": -0.01298131931871671,
          "trades": 7,
          "skipped_capacity": 0,
          "win_rate": 0.14285714285714285,
          "mean_trade_pnl": -18.544741883880786,
          "profit_factor": 0.2569317924298268,
          "maximum_drawdown": -0.014770378424414199,
          "sharpe": -12.091809349861121,
          "sortino": -3.7487811246689335,
          "calmar": -46.14991022571852,
          "cagr": -0.681651638286605,
          "turnover": 1.7380879855505813,
          "exposure": 0.25,
          "average_holding_bars": 2.857142857142857,
          "cost_multiplier": 1.5,
          "base_round_trip_cost": 0.003,
          "max_concurrent_positions": 5,
          "max_portfolio_risk_pct": 5.0,
          "max_gross_exposure_pct": 100.0
        },
        "cost_2x": {
          "starting_capital": 10000.0,
          "ending_capital": 9844.178151293017,
          "portfolio_return": -0.01558218487069829,
          "trades": 7,
          "skipped_capacity": 0,
          "win_rate": 0.14285714285714285,
          "mean_trade_pnl": -22.260264100997517,
          "profit_factor": 0.2088014761256604,
          "maximum_drawdown": -0.016630690070990717,
          "sharpe": -13.539954643617193,
          "sortino": -4.255329031085411,
          "calmar": -44.9379401982412,
          "cagr": -0.7473489558656645,
          "turnover": 1.7365008693661155,
          "exposure": 0.25,
          "average_holding_bars": 2.857142857142857,
          "cost_multiplier": 2.0,
          "base_round_trip_cost": 0.003,
          "max_concurrent_positions": 5,
          "max_portfolio_risk_pct": 5.0,
          "max_gross_exposure_pct": 100.0
        }
      },
      "threshold": -9.457308140196593e-05
    },
    "score": -0.34036516302359515
  },
  "deployable_architecture": "pooled",
  "selected_weight": "none",
  "selected_parameters": {
    "name": "synthetic_d4",
    "iterations": 60,
    "learning_rate": 0.08,
    "depth": 4,
    "l2_leaf_reg": 6.0,
    "random_strength": 0.4,
    "bagging_temperature": 0.4
  },
  "selected_seed": 42,
  "final_metrics": {
    "classification": {
      "positive_class_rate": 0.13261648745519714,
      "precision": 0.125,
      "recall": 0.2972972972972973,
      "f1": 0.176,
      "confusion_matrix": [
        [
          165,
          77
        ],
        [
          26,
          11
        ]
      ],
      "roc_auc": 0.44750949296403847,
      "pr_auc": 0.12081739587268647,
      "log_loss": 0.44662400209689723,
      "brier_score": 0.1351907329559662,
      "single_class_test": false
    },
    "probabilities": {
      "count": 279,
      "unique_count": 277,
      "min": 0.07872050061903599,
      "max": 0.6157663044775069,
      "mean": 0.21566595921809842,
      "std": 0.0932033067511086,
      "range": 0.5370458038584709,
      "q05": 0.10985187519220516,
      "q25": 0.14805562614469472,
      "median": 0.19643114259536765,
      "q75": 0.2596420720598645,
      "q95": 0.38887130375364926,
      "expected_calibration_error": 0.10427591884319339,
      "calibration_curve": [
        {
          "left": 0.0,
          "right": 0.1,
          "count": 11,
          "mean_probability": 0.0944464211181141,
          "positive_rate": 0.36363636363636365
        },
        {
          "left": 0.1,
          "right": 0.2,
          "count": 132,
          "mean_probability": 0.15285089661435072,
          "positive_rate": 0.11363636363636363
        },
        {
          "left": 0.2,
          "right": 0.30000000000000004,
          "count": 94,
          "mean_probability": 0.24215498050800024,
          "positive_rate": 0.14893617021276595
        },
        {
          "left": 0.30000000000000004,
          "right": 0.4,
          "count": 29,
          "mean_probability": 0.3390839248820151,
          "positive_rate": 0.10344827586206896
        },
        {
          "left": 0.4,
          "right": 0.5,
          "count": 8,
          "mean_probability": 0.4426794333061522,
          "positive_rate": 0.125
        },
        {
          "left": 0.5,
          "right": 0.6000000000000001,
          "count": 4,
          "mean_probability": 0.5505924690496813,
          "positive_rate": 0.0
        },
        {
          "left": 0.6000000000000001,
          "right": 0.7000000000000001,
          "count": 1,
          "mean_probability": 0.6157663044775069,
          "positive_rate": 0.0
        }
      ]
    },
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
    "model": {},
    "raw_probability_diagnostics": {
      "positive_rate_baseline": 0.13261648745519714,
      "top_buckets": {
        "top_1pct": {
          "observations": 3,
          "positive_rate": 0.0,
          "lift_over_baseline": 0.0,
          "mean_net_return": -0.007999117194196952,
          "total_net_return": -0.023997351582590854,
          "profit_factor": 0.0
        },
        "top_2pct": {
          "observations": 6,
          "positive_rate": 0.0,
          "lift_over_baseline": 0.0,
          "mean_net_return": -0.012696825460776955,
          "total_net_return": -0.07618095276466173,
          "profit_factor": 0.0
        },
        "top_5pct": {
          "observations": 14,
          "positive_rate": 0.07142857142857142,
          "lift_over_baseline": 0.5386100386100385,
          "mean_net_return": -0.005939977232250472,
          "total_net_return": -0.0831596812515066,
          "profit_factor": 0.242682597085924
        },
        "top_10pct": {
          "observations": 28,
          "positive_rate": 0.07142857142857142,
          "lift_over_baseline": 0.5386100386100385,
          "mean_net_return": -0.00456850937014131,
          "total_net_return": -0.12791826236395668,
          "profit_factor": 0.3612817794075993
        },
        "top_20pct": {
          "observations": 56,
          "positive_rate": 0.08928571428571429,
          "lift_over_baseline": 0.6732625482625483,
          "mean_net_return": -0.006811326977454133,
          "total_net_return": -0.38143431073743145,
          "profit_factor": 0.27346917117047503
        }
      }
    },
    "probability_rank_diagnostics": {
      "positive_rate_baseline": 0.13261648745519714,
      "top_buckets": {
        "top_1pct": {
          "observations": 3,
          "positive_rate": 0.0,
          "lift_over_baseline": 0.0,
          "mean_net_return": -0.007999117194196952,
          "total_net_return": -0.023997351582590854,
          "profit_factor": 0.0
        },
        "top_2pct": {
          "observations": 6,
          "positive_rate": 0.0,
          "lift_over_baseline": 0.0,
          "mean_net_return": -0.012696825460776955,
          "total_net_return": -0.07618095276466173,
          "profit_factor": 0.0
        },
        "top_5pct": {
          "observations": 14,
          "positive_rate": 0.07142857142857142,
          "lift_over_baseline": 0.5386100386100385,
          "mean_net_return": -0.005939977232250472,
          "total_net_return": -0.0831596812515066,
          "profit_factor": 0.242682597085924
        },
        "top_10pct": {
          "observations": 28,
          "positive_rate": 0.07142857142857142,
          "lift_over_baseline": 0.5386100386100385,
          "mean_net_return": -0.00456850937014131,
          "total_net_return": -0.12791826236395668,
          "profit_factor": 0.3612817794075993
        },
        "top_20pct": {
          "observations": 56,
          "positive_rate": 0.08928571428571429,
          "lift_over_baseline": 0.6732625482625483,
          "mean_net_return": -0.006811326977454133,
          "total_net_return": -0.38143431073743145,
          "profit_factor": 0.27346917117047503
        }
      }
    },
    "expected_utility": {
      "reference": {
        "__global__": {
          "expected_win": 0.01882115366943127,
          "expected_loss": -0.013437342668507542,
          "rows": 33
        },
        "breakout": {
          "expected_win": null,
          "expected_loss": -0.024997539375135932,
          "rows": 1
        },
        "mean_reversion": {
          "expected_win": 0.01882115366943127,
          "expected_loss": -0.013009187234928712,
          "rows": 32
        }
      },
      "valid_rows": 257,
      "selected_rows": 12,
      "mean_expected_utility": -0.0060312875709862684,
      "mean_realized_net_return": -0.006062575181764079,
      "total_realized_net_return": -0.07275090218116895,
      "profit_factor": 0.26704998101360233,
      "portfolio": {
        "starting_capital": 10000.0,
        "ending_capital": 9818.943554950778,
        "portfolio_return": -0.018105644504922247,
        "trades": 12,
        "skipped_capacity": 0,
        "win_rate": 0.16666666666666666,
        "mean_trade_pnl": -15.08803708743524,
        "profit_factor": 0.2656259205108898,
        "maximum_drawdown": -0.018105644504922247,
        "sharpe": -9.298014493177327,
        "sortino": -3.1492596041607355,
        "calmar": -21.47928961257558,
        "cagr": -0.3888963819435626,
        "turnover": 2.976241068280816,
        "exposure": 0.25,
        "average_holding_bars": 2.9166666666666665,
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
        "ending_capital": 8927.368035178952,
        "portfolio_return": -0.1072631964821048,
        "trades": 86,
        "skipped_capacity": 2,
        "win_rate": 0.37209302325581395,
        "mean_trade_pnl": -12.47246470722145,
        "profit_factor": 0.37457153824274425,
        "maximum_drawdown": -0.11021623221574406,
        "sharpe": -12.95722929381187,
        "sortino": -6.886440034593824,
        "calmar": -8.071619741725588,
        "cagr": -0.8896235158112115,
        "turnover": 20.010580246808175,
        "exposure": 0.25,
        "average_holding_bars": 2.7674418604651163,
        "cost_multiplier": 1.0,
        "base_round_trip_cost": 0.003,
        "max_concurrent_positions": 5,
        "max_portfolio_risk_pct": 5.0,
        "max_gross_exposure_pct": 100.0
      },
      "cost_1_5x": {
        "starting_capital": 10000.0,
        "ending_capital": 8643.034492571236,
        "portfolio_return": -0.13569655074287634,
        "trades": 86,
        "skipped_capacity": 2,
        "win_rate": 0.313953488372093,
        "mean_trade_pnl": -15.778668691032127,
        "profit_factor": 0.28221653455862894,
        "maximum_drawdown": -0.13598226723300744,
        "sharpe": -16.066798816232705,
        "sortino": -8.619538661047052,
        "calmar": -6.921033170336927,
        "cagr": -0.9411377820972647,
        "turnover": 19.70507671514545,
        "exposure": 0.25,
        "average_holding_bars": 2.7674418604651163,
        "cost_multiplier": 1.5,
        "base_round_trip_cost": 0.003,
        "max_concurrent_positions": 5,
        "max_portfolio_risk_pct": 5.0,
        "max_gross_exposure_pct": 100.0
      },
      "cost_2x": {
        "starting_capital": 10000.0,
        "ending_capital": 8367.46681889391,
        "portfolio_return": -0.16325331811060895,
        "trades": 86,
        "skipped_capacity": 2,
        "win_rate": 0.27906976744186046,
        "mean_trade_pnl": -18.98294396634987,
        "profit_factor": 0.2117944490849858,
        "maximum_drawdown": -0.16325331811060895,
        "sharpe": -18.83251498867881,
        "sortino": -10.234959640044078,
        "calmar": -5.933298941981598,
        "cagr": -0.9686307396206614,
        "turnover": 19.405619026725077,
        "exposure": 0.25,
        "average_holding_bars": 2.7674418604651163,
        "cost_multiplier": 2.0,
        "base_round_trip_cost": 0.003,
        "max_concurrent_positions": 5,
        "max_portfolio_risk_pct": 5.0,
        "max_gross_exposure_pct": 100.0
      },
      "cost_3x": {
        "starting_capital": 10000.0,
        "ending_capital": 7841.590757131133,
        "portfolio_return": -0.21584092428688673,
        "trades": 86,
        "skipped_capacity": 2,
        "win_rate": 0.23255813953488372,
        "mean_trade_pnl": -25.097781893824063,
        "profit_factor": 0.11875092777240037,
        "maximum_drawdown": -0.21584092428688673,
        "sharpe": -23.360009721197223,
        "sortino": -13.257709905344596,
        "calmar": -4.591848507410879,
        "cagr": -0.9911088260249254,
        "turnover": 18.824322737812203,
        "exposure": 0.25,
        "average_holding_bars": 2.7674418604651163,
        "cost_multiplier": 3.0,
        "base_round_trip_cost": 0.003,
        "max_concurrent_positions": 5,
        "max_portfolio_risk_pct": 5.0,
        "max_gross_exposure_pct": 100.0
      },
      "all_signals": {
        "starting_capital": 10000.0,
        "ending_capital": 7616.544129609024,
        "portfolio_return": -0.23834558703909758,
        "trades": 242,
        "skipped_capacity": 37,
        "win_rate": 0.3305785123966942,
        "mean_trade_pnl": -9.848991199962686,
        "profit_factor": 0.43144251920347315,
        "maximum_drawdown": -0.24059112311826092,
        "sharpe": -16.03735606816697,
        "sortino": -10.886189392583445,
        "calmar": -4.126630001874447,
        "cagr": -0.9928305468444842,
        "turnover": 53.56035831963619,
        "exposure": 0.24515479537000442,
        "average_holding_bars": 2.7520661157024793,
        "cost_multiplier": 1.0,
        "base_round_trip_cost": 0.003,
        "max_concurrent_positions": 5,
        "max_portfolio_risk_pct": 5.0,
        "max_gross_exposure_pct": 100.0
      }
    },
    "confidence_intervals": {
      "method": "moving_block_bootstrap",
      "iterations": 5,
      "block_size_bars": 24,
      "confidence_intervals": {
        "roc_auc": {
          "lower_95": 0.4451992183734808,
          "median": 0.4704225352112677,
          "upper_95": 0.5036351373318466
        },
        "pr_auc": {
          "lower_95": 0.09204972298752569,
          "median": 0.13658173308465713,
          "upper_95": 0.15202073503613445
        },
        "precision": {
          "lower_95": 0.08129032258064517,
          "median": 0.12359550561797752,
          "upper_95": 0.1517234219269103
        },
        "win_rate": {
          "lower_95": 0.2510752688172043,
          "median": 0.3372093023255814,
          "upper_95": 0.42504012841091493
        },
        "mean_trade_return": {
          "lower_95": -0.00821219251792717,
          "median": -0.006250935707580121,
          "upper_95": -0.0036008556749684856
        },
        "profit_factor": {
          "lower_95": 0.2332730385171152,
          "median": 0.36998704232527224,
          "upper_95": 0.521822649750868
        },
        "portfolio_return": {
          "lower_95": -0.1498242329216164,
          "median": -0.1250541639121695,
          "upper_95": -0.0977243810749959
        },
        "sharpe": {
          "lower_95": -28.80064845033086,
          "median": -20.496944010319265,
          "upper_95": -15.700165137744827
        }
      }
    }
  },
  "walk_forward": {
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
  },
  "seed_stability": {
    "seeds": [
      42
    ],
    "portfolio_returns": [
      0.00272768777100163
    ],
    "scores": [
      -0.014446535121950509
    ],
    "positive_portfolio_return_rate": 1.0,
    "median_portfolio_return": 0.00272768777100163,
    "worst_portfolio_return": 0.00272768777100163,
    "score_std": 0.0,
    "selected_median_seed": 42
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
  },
  "promotion_ready": false,
  "promotion_reasons": [
    "ROC AUC is not above 0.5",
    "PR AUC does not beat class baseline",
    "too few OOS trades",
    "OOS portfolio return is not positive",
    "OOS portfolio profit factor is too low",
    "OOS mean selected-trade net return is not positive",
    "1.5x cost stress is not positive",
    "2x cost stress is negative",
    "walk-forward positive fold rate is below research minimum",
    "selected trades are concentrated in one strategy"
  ],
  "research_result": "NO ROBUST EDGE FOUND",
  "candidate": null,
  "production_refit": null,
  "model_explanations": {
    "status": "not_run",
    "reason": "candidate did not pass all economic/robustness gates"
  },
  "error_analysis": {
    "rows": 279,
    "selected": 88,
    "false_positive": 77,
    "false_negative": 26,
    "allowed_stop_loss": 18,
    "false_positive_mean_net_return": -0.008226216803789611,
    "false_negative_mean_net_return": 0.01923210716280036,
    "false_positive_by_strategy": {
      "breakout": {
        "count": 5,
        "mean": -0.006594844384767537,
        "sum": -0.032974221923837685
      },
      "mean_reversion": {
        "count": 72,
        "mean": -0.008339506555110586,
        "sum": -0.6004444719679622
      }
    },
    "false_negative_by_strategy": {
      "breakout": {
        "count": 2,
        "mean": 0.017670885814149887,
        "sum": 0.035341771628299774
      },
      "mean_reversion": {
        "count": 24,
        "mean": 0.019362208941854562,
        "sum": 0.4646930146045095
      }
    },
    "false_positive_by_symbol": {
      "ADAUSDT": {
        "count": 11,
        "mean": -0.003914759815939076,
        "sum": -0.04306235797532983
      },
      "BTCUSDT": {
        "count": 14,
        "mean": -0.005221425349223744,
        "sum": -0.07309995488913242
      },
      "ETHUSDT": {
        "count": 34,
        "mean": -0.008545805539641809,
        "sum": -0.2905573883478215
      },
      "SOLUSDT": {
        "count": 18,
        "mean": -0.012594388482195342,
        "sum": -0.22669899267951615
      }
    },
    "false_negative_by_symbol": {
      "ADAUSDT": {
        "count": 8,
        "mean": 0.01674747033456467,
        "sum": 0.13397976267651737
      },
      "BTCUSDT": {
        "count": 5,
        "mean": 0.019659568796646567,
        "sum": 0.09829784398323284
      },
      "ETHUSDT": {
        "count": 5,
        "mean": 0.022848912491670273,
        "sum": 0.11424456245835136
      },
      "SOLUSDT": {
        "count": 8,
        "mean": 0.01918907713933846,
        "sum": 0.15351261711470768
      }
    },
    "false_positive_by_trend_regime": {
      "down": {
        "count": 61,
        "mean": -0.008087449717441358,
        "sum": -0.49333443276392286
      },
      "range": {
        "count": 12,
        "mean": -0.010042983028083926,
        "sum": -0.12051579633700711
      },
      "up": {
        "count": 4,
        "mean": -0.004892116197717481,
        "sum": -0.019568464790869922
      }
    },
    "false_negative_by_trend_regime": {
      "down": {
        "count": 22,
        "mean": 0.019624792246720094,
        "sum": 0.43174542942784205
      },
      "range": {
        "count": 2,
        "mean": 0.016473792588333706,
        "sum": 0.03294758517666741
      },
      "up": {
        "count": 2,
        "mean": 0.017670885814149887,
        "sum": 0.035341771628299774
      }
    },
    "false_positive_by_volatility_regime": {
      "high": {
        "count": 27,
        "mean": -0.005094992154577835,
        "sum": -0.13756478817360154
      },
      "low": {
        "count": 50,
        "mean": -0.009917078114363967,
        "sum": -0.4958539057181984
      }
    },
    "false_negative_by_volatility_regime": {
      "high": {
        "count": 12,
        "mean": 0.021054881682277357,
        "sum": 0.2526585801873283
      },
      "low": {
        "count": 14,
        "mean": 0.017669729003248643,
        "sum": 0.247376206045481
      }
    },
    "false_positive_feature_means": {
      "candle_duration_minutes": 60.0,
      "ret_1": -0.003984886818408702,
      "ret_7": -0.023129893112035987,
      "ret_20": -0.03206776717093712,
      "ret_50": -0.021362743918614445,
      "ret_1h": -0.003984886818408702,
      "ret_3h": -0.010171152848418241,
      "ret_12h": -0.02968508884088556,
      "ret_24h": -0.028441883921953365,
      "return_per_hour": -0.003984886818408702,
      "vol_7": 0.008666130297289496,
      "vol_20": 0.008280640290680716,
      "vol_50": 0.008633947030353282,
      "volatility_per_sqrt_hour": 0.008280640290680716,
      "downside_vol_20": 0.006136356141034736,
      "volume_z_20": 0.27353992485777884,
      "volume_z_50": 0.27129861684292594,
      "volume_per_hour": 1539.4892748905334,
      "volume_trend_20": 0.017346236006285036,
      "price_z_20": -1.4517577569060751,
      "price_z_50": -1.099722907228296,
      "candle_range": 0.02497555009150813,
      "body_size": 0.008853151532232963,
      "rsi_14": 27.80297832279088,
      "atr_14_pct": 0.02158030640519738,
      "atr_per_sqrt_hour": 0.02158030640519738,
      "distance_to_high_50": -0.06951299879258864,
      "distance_to_low_50": 0.027722531568056572,
      "rolling_drawdown_50": -0.06005305118178447,
      "vol_ratio_7_50": 0.9740218853164196,
      "vol_ratio_20_50": 0.9549167475309978,
      "dollar_volume_z_50": 0.1629895225524792,
      "log_dollar_volume": 12.422045857040851,
      "ema_distance_20": -0.01853243445961983,
      "ema_distance_50": -0.021276532651204626,
      "ema_slope_20": -0.0017380745023464102,
      "bollinger_position_20": -0.7258788784530376,
      "momentum_acceleration": -0.011906174602207996
    },
    "false_negative_feature_means": {
      "candle_duration_minutes": 60.0,
      "ret_1": -0.0005417781797932713,
      "ret_7": -0.020464569654466084,
      "ret_20": -0.03818345050846616,
      "ret_50": -0.03434413036180536,
      "ret_1h": -0.0005417781797932713,
      "ret_3h": -0.005548620180858294,
      "ret_12h": -0.03280990489403622,
      "ret_24h": -0.035333961693814364,
      "return_per_hour": -0.0005417781797932713,
      "vol_7": 0.009666631489215892,
      "vol_20": 0.008077452970126554,
      "vol_50": 0.007869059465597026,
      "volatility_per_sqrt_hour": 0.008077452970126554,
      "downside_vol_20": 0.006138291669366705,
      "volume_z_20": 0.2973354861765747,
      "volume_z_50": 0.43753868782666394,
      "volume_per_hour": 1718.141830491826,
      "volume_trend_20": 0.015877214602434894,
      "price_z_20": -1.2554895482613881,
      "price_z_50": -1.4492348031760427,
      "candle_range": 0.023599594591385536,
      "body_size": 0.009444211487609058,
      "rsi_14": 25.70394943555934,
      "atr_14_pct": 0.02223210716280035,
      "atr_per_sqrt_hour": 0.02223210716280035,
      "distance_to_high_50": -0.07382707431284964,
      "distance_to_low_50": 0.022303349914569268,
      "rolling_drawdown_50": -0.06679629584755085,
      "vol_ratio_7_50": 1.19518164602334,
      "vol_ratio_20_50": 1.0124586003491407,
      "dollar_volume_z_50": 0.2884327499012032,
      "log_dollar_volume": 12.522743354953016,
      "ema_distance_20": -0.01963134757628405,
      "ema_distance_50": -0.028189089054886977,
      "ema_slope_20": -0.002137352579589351,
      "bollinger_position_20": -0.6277447741306941,
      "momentum_acceleration": -0.007100361976502929
    }
  },
  "production_trading_ready": false
}
```
