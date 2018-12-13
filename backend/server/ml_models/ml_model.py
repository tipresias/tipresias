"""Base ML model and data classes"""

import os
from typing import Sequence, Optional, Tuple
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.base import BaseEstimator
from sklearn.externals import joblib
import pandas as pd

MODULE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class MLModel:
    """Base ML model class"""

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = (),
        name: Optional[str] = None,
        module_name: str = "",
    ) -> None:

        if not any(estimators):
            raise ValueError("At least one estimator is required, but none were given.")

        self._name = name
        self._module_name = module_name
        self._pipeline: Pipeline = make_pipeline(*estimators)

    @property
    def name(self) -> str:
        """Name of the model"""

        return self._name or self.__last_estimator()[0]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Fit estimator to the data"""

        self._pipeline.fit(X, y)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Make predictions based on the data input"""

        y_pred = self._pipeline.predict(X)

        return pd.Series(y_pred, name="predicted_margin", index=X.index)

    def save(self, filepath: Optional[str] = None) -> None:
        """Save the pipeline as a pickle file"""

        filepath = filepath or os.path.join(
            MODULE_DIR, self._module_name, f"{self.name}.pkl"
        )

        joblib.dump(self._pipeline, filepath)

    def load(self, filepath: Optional[str] = None) -> None:
        """Load the pipeline from a pickle file"""

        filepath = filepath or os.path.join(
            MODULE_DIR, self._module_name, f"{self.name}.pkl"
        )

        self._pipeline = joblib.load(filepath)

    def __last_estimator(self) -> Tuple[str, BaseEstimator]:
        return self._pipeline.steps[-1]
