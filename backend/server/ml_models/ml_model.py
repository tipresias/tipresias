"""Base ML model and data classes"""

import os
import sys
from typing import Optional, Tuple, Union, List, Type
from functools import reduce
from sklearn.pipeline import Pipeline
from sklearn.utils.metaestimators import _BaseComposition
from sklearn.base import RegressorMixin
import pandas as pd
import numpy as np

from project.settings.common import BASE_DIR
from server.types import YearPair, DataFrameTransformer, M


class MLModel(_BaseComposition, RegressorMixin):
    """Base ML model class"""

    def __init__(self, pipeline: Pipeline, name: Optional[str] = None) -> None:
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

        module_path = self.__module__
        module_filepath = sys.modules[module_path].__file__

        return os.path.abspath(
            os.path.join(BASE_DIR, os.path.dirname(module_filepath), f"{self.name}.pkl")
        )

    def fit(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]
    ) -> Type[M]:
        """Fit estimator to the data"""

        self.pipeline.fit(X, y)

        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Make predictions based on the data input"""

        return self.pipeline.predict(X)


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
        features = data_frame.drop(["score", "oppo_score"], axis=1)
        numeric_features = features.select_dtypes(np.number).astype(float)
        categorical_features = features.drop(numeric_features.columns, axis=1)

        return pd.concat([categorical_features, numeric_features], axis=1)

    @staticmethod
    def __y(data_frame: pd.DataFrame) -> pd.Series:
        return (data_frame["score"] - data_frame["oppo_score"]).rename("margin")


class DataTransformerMixin:
    """Mixin class for MLModelData classes that use data transformers"""

    @property
    def data_transformers(self) -> List[DataFrameTransformer]:
        """List of data transformer functions"""

        raise NotImplementedError("The data_transformers() method must be defined.")

    @property
    def _compose_transformers(self) -> DataFrameTransformer:
        """Combine data transformation functions via composition"""

        # Need to reverse the transformation steps, because composition makes the output
        # of each new function the argument for the previous
        return reduce(
            self.__compose_two_transformers,
            reversed(self.data_transformers),
            lambda x: x,
        )

    @staticmethod
    def __compose_two_transformers(
        composed_func: DataFrameTransformer, func_element: DataFrameTransformer
    ) -> DataFrameTransformer:
        return lambda x: composed_func(func_element(x))
