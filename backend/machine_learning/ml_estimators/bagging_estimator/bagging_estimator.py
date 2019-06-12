"""Class for model trained on all AFL data and its associated data class"""

from typing import Optional
import numpy as np
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import BaggingRegressor
from xgboost import XGBRegressor

from machine_learning.data_config import TEAM_NAMES, ROUND_TYPES, VENUES, CATEGORY_COLS
from machine_learning.ml_estimators.sklearn import CorrelationSelector
from .. import BaseMLEstimator

SEED = 42
np.random.seed(SEED)

BEST_PARAMS = {
    "baggingregressor__base_estimator__booster": "dart",
    "baggingregressor__base_estimator__colsample_bylevel": 0.9593085973720467,
    "baggingregressor__base_estimator__colsample_bytree": 0.8366869579732328,
    "baggingregressor__base_estimator__learning_rate": 0.13118764001091077,
    "baggingregressor__base_estimator__max_depth": 6,
    "baggingregressor__base_estimator__n_estimators": 149,
    "baggingregressor__base_estimator__reg_alpha": 0.07296244459829336,
    "baggingregressor__base_estimator__reg_lambda": 0.11334834444556088,
    "baggingregressor__base_estimator__subsample": 0.8285733635843882,
    "baggingregressor__n_estimators": 7,
    "correlationselector__threshold": 0.030411689885916048,
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
                    handle_unknown="ignore",
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
