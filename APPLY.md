# APPLY — MVP-5 validation package

Target branch: `feature/news-agent-full-mvp`.

This package contains only feature-freeze work: regression fixes, tests, CI, documentation and packaging metadata. It does not add trading features and does not start price+news training.

## Apply

Extract the archive into the repository root with replacement, then apply the two-line ML compatibility patch:

```bash
python APPLY_MVP5.py

# or, equivalently:
# git apply MVP5_REGRESSION_FIX.patch
```

Then:

```bash
cp .env.example .env
python scripts/test_all.py
docker compose config
docker compose build backend ml_service
docker compose up -d
```

Open `http://localhost:8000/`.

## Why the patch exists

The current MVP-4 branch CI exposed a pandas 3 categorical dtype regression in CatBoost preparation. The patch forces categorical columns back to plain `object` dtype. The proposed CI also fixes the ML import-path contract by running ML tests with `PYTHONPATH=app/ml_services` or via `scripts/test_all.py`.
