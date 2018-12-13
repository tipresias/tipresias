"""Class for model trained on all AFL data and its associated data class"""

from typing import List, Tuple, Union, Callable, Sequence, Optional
from datetime import datetime
from functools import reduce
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from server.ml_models.betting_model import BettingModelData
from server.ml_models.match_model import MatchModelData
from server.ml_models.player_model import PlayerModelData
from server.ml_models.ml_model import MLModel
from server.types import YearsType


START_DATE = "1965-01-01"
DATA_KWARGS = {"train_years": (None, None), "test_years": (None, None)}
DATA_READERS: List[Callable] = [
    BettingModelData(**DATA_KWARGS).data,
    PlayerModelData(start_date=START_DATE, **DATA_KWARGS).data,
    MatchModelData(**DATA_KWARGS).data,
]
MODEL_ESTIMATORS = (StandardScaler(), XGBRegressor())

np.random.seed(42)


class AllModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on all AFL data"""

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = MODEL_ESTIMATORS,
        name: Optional[str] = None,
        module_name: str = "",
    ) -> None:
        super().__init__(estimators=estimators, name=name, module_name=module_name)


class AllModelData:
    """Load and clean data for the XGBRegressor pipeline.

    Args:
        train_years (tuple[integer or None]): Minimum and maximum (inclusive) years
            for the training data.
        test_years (tuple[ingeter or None]): Minimum and maximum (inclusive) years
            for the test data.

    Attributes:
        data (pandas.DataFrame): Cleaned, unfiltered data frame.
        train_years (tuple[integer or None]): Minimum and maximum (inclusive) years
            for the training data.
        test_years (tuple[ingeter or None]): Minimum and maximum (inclusive) years
            for the test data.
    """

    def __init__(
        self,
        data_readers: List[Callable] = DATA_READERS,
        train_years: YearsType = (None, 2015),
        test_years: YearsType = (2016, 2016),
        start_date=None,
        end_date="2016-12-31",
    ) -> None:
        self._train_years = train_years
        self._test_years = test_years

        data_frame = reduce(self.__concat_data_frames, data_readers)
        data_frame_dtypes = data_frame.dtypes
        numeric_cols = data_frame_dtypes[
            (data_frame_dtypes == float) | (data_frame_dtypes == int)
        ]
        fillna_dict = {col: 0 for col in numeric_cols}
        start_year = datetime.strptime(start_date, "%Y-%m-%d").year if start_date else 0
        end_year = (
            datetime.strptime(end_date, "%Y-%m-%d").year if start_date else np.Inf
        )

        self.data = (
            data_frame[
                (data_frame["year"] >= start_year) & (data_frame["year"] <= end_year)
            ]
            .fillna(fillna_dict)
            .dropna()
        )

    def train_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Filter data by year to produce training data.

        Returns:
            Tuple[pandas.DataFrame]: Training features and labels.
        """

        data_train = self.data[
            (self.data["year"] >= self.__train_min())
            & (self.data["year"] <= self.__train_max())
        ]

        X_train = self.__X(data_train)
        y_train = self.__y(data_train)

        return X_train, y_train

    def test_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Filter data by year to produce test data.

        Returns:
            Tuple[pandas.DataFrame]: Test features and labels.
        """

        data_test = self.data[
            (self.data["year"] >= self.__test_min())
            & (self.data["year"] <= self.__test_max())
        ]
        X_test = self.__X(data_test)
        y_test = self.__y(data_test)

        return X_test, y_test

    @property
    def train_years(self) -> YearsType:
        """Range of years for slicing training data"""

        return self._train_years

    @train_years.setter
    def train_years(self, years: YearsType) -> None:
        self._train_years = years

    @property
    def test_years(self) -> YearsType:
        """Range of years for slicing test data"""

        return self._test_years

    @test_years.setter
    def test_years(self, years: YearsType) -> None:
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

    @staticmethod
    def __id_col(df):
        return (
            df["player_id"].astype(str)
            + df["match_id"].astype(str)
            + df["year"].astype(str)
        )

    @staticmethod
    def __concat_data_frames(concated_data_frame, data_frame):
        if concated_data_frame is None:
            return data_frame

        agg_cols = set(concated_data_frame.columns)
        df_cols = set(data_frame.columns)
        drop_cols = agg_cols.intersection(df_cols)

        # Have to drop shared columns, and this seems a reasonable way of doing it
        # without hard-coding values
        return pd.concat(
            [concated_data_frame.drop(list(drop_cols), axis=1), data_frame], axis=1
        )
