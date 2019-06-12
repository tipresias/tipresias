"""Class for model trained on all AFL data and its associated data class"""

import warnings
from typing import Optional

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.exceptions import DataConversionWarning
from xgboost import XGBRegressor

from machine_learning.data_config import (
    TEAM_NAMES,
    ROUND_TYPES,
    VENUES,
    SEED,
    CATEGORY_COLS,
)
from .. import BaseMLEstimator

PIPELINE = make_pipeline(
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
    XGBRegressor(),
)

# Using ColumnTransformer to run OneHotEncoder & StandardScaler causes this warning
# when using BaggingRegressor, because BR converts the DataFrame to a numpy array,
# which results in all rows having type 'object', because they include strings and floats
warnings.simplefilter("ignore", DataConversionWarning)

np.random.seed(SEED)


class BenchmarkEstimator(BaseMLEstimator):
    """Create pipeline for fitting/predicting with model trained on all AFL data"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)
