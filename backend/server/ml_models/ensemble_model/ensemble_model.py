"""Class for model trained on all AFL data and its associated data class"""

from typing import Optional
import numpy as np
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import BaggingRegressor
from xgboost import XGBRegressor

from server.ml_models.ml_model import MLModel
from server.ml_models.data_config import TEAM_NAMES, ROUND_TYPES

BEST_PARAMS = {
    "baggingregressor__base_estimator__booster": "dart",
    "baggingregressor__base_estimator__colsample_bylevel": 0.932410481813671,
    "baggingregressor__base_estimator__colsample_bytree": 0.8477673728891532,
    "baggingregressor__base_estimator__learning_rate": 0.12003700927898357,
    "baggingregressor__base_estimator__max_depth": 4,
    "baggingregressor__base_estimator__n_estimators": 90,
    "baggingregressor__base_estimator__reg_alpha": 0.025859007817833925,
    "baggingregressor__base_estimator__reg_lambda": 0.9186496206570707,
    "baggingregressor__base_estimator__subsample": 0.9130436248456849,
    "baggingregressor__n_estimators": 10,
}
PIPELINE = make_pipeline(
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(
                    categories=[TEAM_NAMES, TEAM_NAMES, ROUND_TYPES], sparse=False
                ),
                ["team", "oppo_team", "round_type"],
            )
        ],
        remainder="passthrough",
    ),
    StandardScaler(),
    BaggingRegressor(base_estimator=XGBRegressor()),
).set_params(**BEST_PARAMS)

np.random.seed(42)


class EnsembleModel(MLModel):
    """Model for averaging predictions of an ensemble of models"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)
