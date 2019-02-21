"""Base ML model and data classes"""

import os
import sys
from typing import Optional, Tuple, Union, Type
from sklearn.pipeline import Pipeline
from sklearn.utils.metaestimators import _BaseComposition
from sklearn.base import RegressorMixin
from sklearn.externals import joblib
import pandas as pd
import numpy as np

from project.settings.common import BASE_DIR
from server.types import YearPair, R


class MLModel(_BaseComposition, RegressorMixin):
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
        save_path = filepath or os.path.join(
            self._default_directory(), f"{self.name}.pkl"
        )

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


class MLModelData:
    """Base class for model data"""

    @classmethod
    def class_path(cls):
        return f"{cls.__module__}.{cls.__name__}"

    def __init__(
        self, train_years: YearPair = (None, 2015), test_years: YearPair = (2016, 2016)
    ) -> None:
        self._train_years = train_years
        self._test_years = test_years

    def train_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Filter data by year to produce training data"""

        data_train = self.data.loc[
            (slice(None), slice(*self.train_years), slice(None)), :
        ]

        X_train = self.__X(data_train)
        y_train = self.__y(data_train)

        return X_train, y_train

    def test_data(self, test_round=None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Filter data by year to produce test data"""

        data_test = self.data.loc[
            (slice(None), slice(*self.test_years), slice(test_round, test_round)), :
        ]
        X_test = self.__X(data_test)
        y_test = self.__y(data_test)

        return X_test, y_test

    @property
    def data(self) -> pd.DataFrame:
        """Get the data frame"""

        raise NotImplementedError("The data() method must be defined.")

    @property
    def train_years(self) -> YearPair:
        """Range of years for slicing training data"""

        return self._train_years

    @train_years.setter
    def train_years(self, years: YearPair) -> None:
        self._train_years = years

    @property
    def test_years(self) -> YearPair:
        """Range of years for slicing test data"""

        return self._test_years

    @test_years.setter
    def test_years(self, years: YearPair) -> None:
        self._test_years = years

    @staticmethod
    def __X(data_frame: pd.DataFrame) -> pd.DataFrame:
        labels = [
            "(?:oppo_)*score",
            "(?:oppo_)*behinds",
            "(?:oppo_)*goals",
            "(?:oppo_)*margin",
            "(?:oppo_)*result",
        ]
        label_cols = data_frame.filter(regex=f"^{'$|^'.join(labels)}$").columns
        features = data_frame.drop(label_cols, axis=1)
        numeric_features = features.select_dtypes("number").astype(float)
        categorical_features = features.select_dtypes(exclude=["number", "datetime"])

        # Sorting columns with categorical features first to allow for positional indexing
        # for some data transformations further down the pipeline
        return pd.concat([categorical_features, numeric_features], axis=1)

    @staticmethod
    def __y(data_frame: pd.DataFrame) -> pd.Series:
        return (data_frame["score"] - data_frame["oppo_score"]).rename("margin")
