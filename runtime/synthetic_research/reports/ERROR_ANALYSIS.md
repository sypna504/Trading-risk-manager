# Error Analysis

- **generated_at:** 2026-08-26T20:03:13.730736+00:00
- **source_ref:** feature/auto-signal-choseing + research patch
- **git_sha:** NOT CAPTURED
- **history_sha256:** 1b31deeb587a7a087008478e8b0a8a73a9ea5b24b145022c6273706df91ba453
- **history_period:** 2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00
- **mode:** quick

{
  "rank_diagnostics": {
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
  "confusion": [
    [
      165,
      77
    ],
    [
      26,
      11
    ]
  ],
  "false_positive_false_negative": {
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
  }
}
