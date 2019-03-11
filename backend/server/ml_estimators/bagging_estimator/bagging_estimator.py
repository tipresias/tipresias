"""Class for model trained on all AFL data and its associated data class"""

from typing import Optional
import numpy as np
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import BaggingRegressor
from xgboost import XGBRegressor

from server.data_config import TEAM_NAMES, ROUND_TYPES, VENUES, CATEGORY_COLS
from server.ml_estimators.sklearn import CorrelationSelector
from .. import BaseMLEstimator

SEED = 42
np.random.seed(SEED)

BEST_PARAMS = {
    "baggingregressor__base_estimator__booster": "dart",
    "baggingregressor__base_estimator__colsample_bylevel": 0.9471809226392005,
    "baggingregressor__base_estimator__colsample_bytree": 0.9696256190933767,
    "baggingregressor__base_estimator__learning_rate": 0.10491107558650835,
    "baggingregressor__base_estimator__max_depth": 4,
    "baggingregressor__base_estimator__n_estimators": 110,
    "baggingregressor__base_estimator__reg_alpha": 0.08214627818071266,
    "baggingregressor__base_estimator__reg_lambda": 0.12815784540554037,
    "baggingregressor__base_estimator__subsample": 0.9821248007080609,
    "baggingregressor__n_estimators": 10,
    "correlationselector__threshold": 0.036836347033957516,
}
PIPELINE = make_pipeline(
    CorrelationSelector(cols_to_keep=CATEGORY_COLS),
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(
                    categories=[TEAM_NAMES, TEAM_NAMES, ROUND_TYPES, VENUES],
                    sparse=False,
                ),
                CATEGORY_COLS,
            )
        ],
        remainder=StandardScaler(),
    ),
    BaggingRegressor(base_estimator=XGBRegressor(seed=SEED)),
).set_params(**BEST_PARAMS)


class BaggingEstimator(BaseMLEstimator):
    """Model for averaging predictions of an ensemble of models"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)
