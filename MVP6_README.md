# Trading Risk Manager — MVP-6 overlay

Apply this ZIP over the completed MVP-5 repository root.

## What this checkpoint adds

- leakage-safe market + news feature merge;
- 1h/3h/6h/12h/24h news windows;
- sentiment, shock, risk, source-diversity, novelty, disagreement and asset-specific features;
- price-only, news-only, fusion, risk-overlay, stacking, veto and context-only experiments;
- LogisticRegression/CatBoost/XGBoost/LightGBM comparison when dependencies are available;
- final-holdout isolation;
- walk-forward, seed stability, block bootstrap, cost stress and concentration summaries;
- requested ablation reports;
- deterministic synthetic runner;
- regression tests for time leakage and reproducibility.

## Quick validation

```bash
python -m compileall -q app/ml_services/app/research tests/news_research scripts/news_fusion_synthetic.py scripts/news_fusion_research.py
PYTHONPATH=. pytest -q tests/news_research/test_news_fusion.py
PYTHONPATH=. python scripts/news_fusion_synthetic.py
```

## Real historical research

Use a point-in-time news export if available. Market input supports CSV/JSONL/parquet:

```bash
PYTHONPATH=. python scripts/news_fusion_research.py   --market app/ml_services/app/training/data/ml_dataset_v3.parquet   --news path/to/historical_news.parquet   --output runtime/news_fusion/report.json
```

or an SQLite database containing `news_items`:

```bash
PYTHONPATH=. python scripts/news_fusion_research.py   --market app/ml_services/app/training/data/ml_dataset_v3.parquet   --news-db path/to/trading_risk.db
```

The runner stays `evidence_scope=research_only`; it never changes production settings or `trade_allowed` automatically.

## Production isolation

This overlay does **not** modify:

- trading decision router;
- risk service;
- online ML predictor;
- active model registry;
- production feature schema.

MVP-7 is intentionally not included.
