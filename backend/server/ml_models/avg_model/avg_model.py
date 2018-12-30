"""Class for model trained on all AFL data and its associated data class"""

from typing import Sequence, Optional
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, Lasso
from sklearn.svm import LinearSVR
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from xgboost import XGBRegressor

from server.ml_models.ml_model import MLModel
from server.ml_models.sklearn import AveragingRegressor

ESTIMATORS = [
    Ridge(),
    GradientBoostingRegressor(),
    LinearSVR(),
    XGBRegressor(),
    Lasso(),
    RandomForestRegressor(n_estimators=100),
]
MODEL_ESTIMATORS = (StandardScaler(), AveragingRegressor(ESTIMATORS))

np.random.seed(42)


class AvgModel(MLModel):
    """Model for averaging predictions of an ensemble of models"""

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = MODEL_ESTIMATORS,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(estimators=estimators, name=name)
