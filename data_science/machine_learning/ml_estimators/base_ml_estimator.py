"""Base ML model and data classes"""

import os
import sys
from typing import Optional, Union, Type
from sklearn.pipeline import Pipeline
from sklearn.utils.metaestimators import _BaseComposition
from sklearn.base import RegressorMixin
from sklearn.externals import joblib
import pandas as pd
import numpy as np

from machine_learning.settings import BASE_DIR
from machine_learning.types import R


class BaseMLEstimator(_BaseComposition, RegressorMixin):
    """Base ML model class"""

    def __init__(
        self, pipeline: Optional[Pipeline] = None, name: Optional[str] = None
    ) -> None:
        super().__init__()

        self._name = name
        self.pipeline = pipeline

    @property
    def name(self) -> str:
        """Name of the model"""

        return self._name or self.__class__.__name__

    def pickle_filepath(self, filepath: str = None) -> str:
        """Filepath to the model's saved pickle file"""

        if filepath is not None:
            return filepath

        return os.path.join(self._default_directory(), f"{self.name}.pkl")

    def dump(self, filepath: str = None) -> None:
        save_path = filepath or self.pickle_filepath()

        joblib.dump(self, save_path)

    def fit(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]
    ) -> Type[R]:
        """Fit estimator to the data"""

        if self.pipeline is None:
            raise TypeError("pipeline must be a scikit learn estimator but is None")

        self.pipeline.fit(X, y)

        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Make predictions based on the data input"""

        if self.pipeline is None:
            raise TypeError("pipeline must be a scikit learn estimator but is None")

        return self.pipeline.predict(X)

    def _default_directory(self) -> str:
        module_path = self.__module__
        module_filepath = sys.modules[module_path].__file__

        return os.path.abspath(os.path.join(BASE_DIR, os.path.dirname(module_filepath)))
