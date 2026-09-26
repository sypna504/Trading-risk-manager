# APPLY MVP-6

Baseline: completed MVP-1 → MVP-5 repository.

This archive is an **overlay**. Extract it into the repository root with replacement.

MVP-6 does not modify production decision logic, risk sizing, active model registry, or the online feature schema.

## Validate

```bash
python -m compileall -q app/ml_services/app/research tests/news_research scripts/news_fusion_synthetic.py scripts/news_fusion_research.py
PYTHONPATH=. pytest -q tests/news_research/test_news_fusion.py
PYTHONPATH=. python scripts/news_fusion_synthetic.py
```

## Historical research

```bash
PYTHONPATH=. python scripts/news_fusion_research.py \
  --market app/ml_services/app/training/data/ml_dataset_v3.parquet \
  --news path/to/point_in_time_news.parquet \
  --output runtime/news_fusion/report.json
```

The historical news input must be point-in-time safe. If only the current edited article body exists, the merge treats the row as known no earlier than `edited_at`.

## Stop condition

Do not start MVP-7 until MVP-6 results have been reviewed.
