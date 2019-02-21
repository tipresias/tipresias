"""Class for model trained on all AFL data and its associated data class"""

from typing import Optional
import numpy as np
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import BaggingRegressor
from xgboost import XGBRegressor

from server.ml_models.ml_model import MLModel
from server.data_config import TEAM_NAMES, ROUND_TYPES, VENUES
from server.ml_models.match_model import CATEGORY_COLS
from server.ml_models.sklearn import CorrelationSelector

SEED = 42
np.random.seed(SEED)

BEST_PARAMS = {
    "baggingregressor__base_estimator__booster": "dart",
    "baggingregressor__base_estimator__colsample_bylevel": 0.9366527037650917,
    "baggingregressor__base_estimator__colsample_bytree": 0.9219993315565242,
    "baggingregressor__base_estimator__learning_rate": 0.11665974558680822,
    "baggingregressor__base_estimator__max_depth": 4,
    "baggingregressor__base_estimator__n_estimators": 110,
    "baggingregressor__base_estimator__reg_alpha": 0.03644721755761247,
    "baggingregressor__base_estimator__reg_lambda": 1.1276807051588262,
    "baggingregressor__base_estimator__subsample": 0.885031174898249,
    "baggingregressor__n_estimators": 10,
    "correlationselector__threshold": 0.038121046704238715,
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


class EnsembleModel(MLModel):
    """Model for averaging predictions of an ensemble of models"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)
