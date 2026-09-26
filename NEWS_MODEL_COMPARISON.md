# NEWS MODEL COMPARISON — MVP-6

## Architecture selection

Selection is performed on the development/selection partition only. The final holdout is not used to select the architecture.

| Architecture | ROC AUC | PR AUC | Brier | Portfolio return | PF |
|---|---:|---:|---:|---:|---:|
| logistic | 0.8977 | 0.8390 | 0.1393 | 26.54% | 4.7082 |
| catboost | 0.8887 | 0.8043 | 0.1455 | 26.80% | 4.2337 |
| xgboost | 0.8626 | 0.7782 | 0.1642 | 28.03% | 4.8645 |
| lightgbm | 0.8583 | 0.7833 | 0.1669 | 25.71% | 4.0032 |

Selected on the synthetic fixture: **logistic**.

Models supported by the MVP-6 comparison layer:

- LogisticRegression;
- CatBoost;
- XGBoost when installed;
- LightGBM when installed;
- logistic stacking of price probability + news probability.

Deep learning is intentionally not used.

This comparison is synthetic pipeline validation only. Real-data model superiority remains **NOT PROVEN**.
