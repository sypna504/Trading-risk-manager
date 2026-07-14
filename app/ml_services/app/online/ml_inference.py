import json
from pathlib import Path

import pandas as pd
from catboost import CatBoostClassifier
from catboost import Pool

from ..config import settings


class ModelPredictor:
    def __init__(self,model_path: str,config_path: str,):
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"model not found: {self.model_path}"
            )

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"model config not found: "
                f"{self.config_path}"
            )

        self.config = json.loads(
            self.config_path.read_text(
                encoding="utf-8"
            )
        )

        self.feature_columns = self.config[
            "feature_cols"
        ]

        self.cat_features = self.config[
            "cat_features"
        ]

        self.threshold = float(
            self.config["threshold"]
        )

        self.model_version = self.config[
            "model_version"
        ]

        self.model = CatBoostClassifier()

        self.model.load_model(
            self.model_path
        )

    def predict(self,features: pd.DataFrame,):
        missing_features = [
            column
            for column in self.feature_columns
            if column not in features.columns
        ]

        if missing_features:
            raise ValueError(
                f"missing model features: "
                f"{missing_features}"
            )

        model_features = features[
            self.feature_columns
        ].copy()

        for column in self.cat_features:
            model_features[column] = (
                model_features[column]
                .astype(str)
            )

        pool = Pool(
            data=model_features,
            cat_features=self.cat_features,
        )

        probability = float(
            self.model.predict_proba(
                pool
            )[0, 1]
        )

        risk_score = 1 - probability

        trade_allowed = (
            probability >= self.threshold
        )

        if probability >= 0.65:
            risk_level = "low"
        elif probability >= 0.50:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "prob_good_trade": probability,
            "risk_score": risk_score,
            "trade_allowed": trade_allowed,
            "threshold": self.threshold,
            "risk_level": risk_level,
            "model_version": self.model_version,
        }


predictor = ModelPredictor(
    model_path=settings.MODEL_PATH,
    config_path=settings.MODEL_CONFIG_PATH,
)