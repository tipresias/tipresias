from typing import Sequence, Type, List, Union, Optional

import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin

from server.types import M


class AveragingRegressor(BaseEstimator, RegressorMixin):
    """Scikit-Learn-style ensemble regressor for averaging regressors' predictions"""

    def __init__(
        self, estimators: Sequence[Type[M]], weights: Optional[List[float]] = None
    ) -> None:
        self.estimators = estimators
        self.weights = weights

        self.__validate_estimators_weights_equality()

    def fit(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]
    ) -> Type[M]:
        """Fit estimators to data"""

        self.__validate_estimators_weights_equality()

        for estimator in self.estimators:
            estimator.fit(X, y)

        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predict with each estimator, then average the predictions"""

        self.__validate_estimators_weights_equality()

        predictions = [estimator.predict(X) for estimator in self.estimators]

        return np.average(np.array(predictions), axis=0, weights=self.weights)

    def __validate_estimators_weights_equality(self):
        if self.weights and len(self.estimators) != len(self.weights):
            raise ValueError(
                f"Received {len(self.estimators)} estimators and {len(self.weights)}"
                "weight values, but they must have the same number."
            )
