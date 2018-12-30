"""Base ML model and data classes"""

import os
from typing import Sequence, Optional, Tuple, Union, List, Type
from functools import reduce
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.externals import joblib
import pandas as pd
import numpy as np

from project.settings.common import BASE_DIR
from server.types import YearPair, DataFrameTransformer, M


class MLModel(BaseEstimator, RegressorMixin):
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
        self.module_name = module_name
        self.estimators = estimators
        self._pipeline: Pipeline = make_pipeline(*estimators)

    @property
    def name(self) -> str:
        """Name of the model"""

        return self._name or self.__class__.__name__

    @property
    def pickle_filepath(self) -> str:
        """Filepath to the model's saved pickle file"""

        return os.path.join(BASE_DIR, os.path.dirname(__file__), f"{self.name}.pkl")

    def fit(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]
    ) -> Type[M]:
        """Fit estimator to the data"""

        self._pipeline.fit(X, y)

        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Make predictions based on the data input"""

        return self._pipeline.predict(X)

    def save(self) -> None:
        """Save the pipeline as a pickle file"""

        joblib.dump(self._pipeline, self.pickle_filepath)

    def load(self) -> None:
        """Load the pipeline from a pickle file"""

        self._pipeline = joblib.load(self.pickle_filepath)


class MLModelData:
    """Base class for model data"""

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

    def __X(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        data_dummies = pd.get_dummies(self.data.select_dtypes("O"))
        X_data = pd.get_dummies(data_frame.drop(["score", "oppo_score"], axis=1))

        # Have to get missing dummy columns, because train & test years can have different
        # teams/venues, resulting in data mismatch when trying to predict with a model
        missing_cols = np.setdiff1d(data_dummies.columns, X_data.columns)
        missing_df = pd.DataFrame(
            {missing_col: 0 for missing_col in missing_cols}, index=X_data.index
        )

        return pd.concat([X_data, missing_df], axis=1).astype(float).sort_index()

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
