"""Base ML model and data classes"""

import os
from typing import Sequence, Optional, Tuple, Union
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.base import BaseEstimator
from sklearn.externals import joblib
import pandas as pd
import numpy as np

from server.types import YearPair

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


class MLModelData:
    """Base class for model data"""

    def __init__(
        self, train_years: YearPair = (None, 2015), test_years: YearPair = (2016, 2016)
    ) -> None:
        self._train_years = train_years
        self._test_years = test_years

    def train_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Filter data by year to produce training data"""

        data_train = self.data[
            (self.data["year"] >= self.__train_min())
            & (self.data["year"] <= self.__train_max())
        ]

        X_train = self.__X(data_train)
        y_train = self.__y(data_train)

        return X_train, y_train

    def test_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Filter data by year to produce test data"""

        data_test = self.data[
            (self.data["year"] >= self.__test_min())
            & (self.data["year"] <= self.__test_max())
        ]
        X_test = self.__X(data_test)
        y_test = self.__y(data_test)

        return X_test, y_test

    @property
    def data(self) -> None:
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

    def __train_min(self) -> Union[int, float]:
        return self._train_years[0] or np.NINF

    def __train_max(self) -> Union[int, float]:
        return self._train_years[1] or np.Inf

    def __test_min(self) -> Union[int, float]:
        return self._test_years[0] or np.NINF

    def __test_max(self) -> Union[int, float]:
        return self._test_years[1] or np.Inf

    def __X(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        data_dummies = pd.get_dummies(self.data.select_dtypes("O"))
        X_data = pd.get_dummies(data_frame.drop(["score", "oppo_score"], axis=1))

        # Have to get missing dummy columns, because train & test years can have different
        # teams/venues, resulting in data mismatch when trying to predict with a model
        missing_cols = np.setdiff1d(data_dummies.columns, X_data.columns)
        missing_df = pd.DataFrame(
            {missing_col: 0 for missing_col in missing_cols}, index=X_data.index
        )

        return pd.concat([X_data, missing_df], axis=1).astype(float)

    @staticmethod
    def __y(data_frame: pd.DataFrame) -> pd.Series:
        return data_frame["score"] - data_frame["oppo_score"]
