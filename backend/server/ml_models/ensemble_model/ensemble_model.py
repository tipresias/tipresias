"""Class for model trained on all AFL data and its associated data class"""

from typing import Optional
import numpy as np
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import BaggingRegressor
from xgboost import XGBRegressor

from server.ml_models.ml_model import MLModel

BEST_PARAMS = {
    "base_estimator__pipeline__xgbregressor__booster": "dart",
    "base_estimator__pipeline__xgbregressor__colsample_bylevel": 0.932410481813671,
    "base_estimator__pipeline__xgbregressor__colsample_bytree": 0.8477673728891532,
    "base_estimator__pipeline__xgbregressor__learning_rate": 0.12003700927898357,
    "base_estimator__pipeline__xgbregressor__max_depth": 4,
    "base_estimator__pipeline__xgbregressor__n_estimators": 90,
    "base_estimator__pipeline__xgbregressor__reg_alpha": 0.025859007817833925,
    "base_estimator__pipeline__xgbregressor__reg_lambda": 0.9186496206570707,
    "base_estimator__pipeline__xgbregressor__subsample": 0.9130436248456849,
    "n_estimators": 10,
}
PIPELINE = make_pipeline(
    StandardScaler(),
    BaggingRegressor(base_estimator=XGBRegressor()).set_params(**BEST_PARAMS),
)

np.random.seed(42)


class EnsembleModel(MLModel):
    """Model for averaging predictions of an ensemble of models"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)
