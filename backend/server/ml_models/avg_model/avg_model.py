"""Class for model trained on all AFL data and its associated data class"""

from typing import Optional
import numpy as np
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, Lasso
from sklearn.svm import LinearSVR
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from xgboost import XGBRegressor

from server.ml_models.ml_model import MLModel
from server.ml_models.sklearn import AveragingRegressor

ESTIMATORS = [
    ("ridge", Ridge()),
    ("gradientboostingregressor", GradientBoostingRegressor()),
    ("linearsvr", LinearSVR()),
    ("xgbregressor", XGBRegressor()),
    ("lasso", Lasso()),
    ("randomforestregressor", RandomForestRegressor(n_estimators=100)),
]
MODEL_ESTIMATORS = (StandardScaler(), AveragingRegressor(ESTIMATORS))
PIPELINE = make_pipeline(*MODEL_ESTIMATORS)

np.random.seed(42)


class AvgModel(MLModel):
    """Model for averaging predictions of an ensemble of models"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)
