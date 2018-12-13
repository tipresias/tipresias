"""Module with wrapper class for XGBoost model and its associated data class"""

from typing import List, Tuple, Optional, Union, Sequence, Callable
from functools import reduce
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator
from xgboost import XGBRegressor

from server.types import FeatureFunctionType, YearsType
from server.data_processors import TeamDataStacker, FeatureBuilder, OppoFeatureBuilder
from server.data_processors.feature_functions import (
    add_last_week_result,
    add_last_week_score,
    add_cum_percent,
    add_cum_win_points,
    add_rolling_last_week_win_rate,
    add_ladder_position,
    add_win_streak,
    add_out_of_state,
    add_travel_distance,
    add_last_week_goals,
    add_last_week_behinds,
)
from server.data_processors import FitzroyDataReader
from server.ml_models.ml_model import MLModel

COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
INDEX_COLS = ["team", "year", "round_number"]
REQUIRED_COLS: List[str] = ["year", "score", "oppo_score"]
FEATURE_FUNCS: Sequence[FeatureFunctionType] = [
    add_out_of_state,
    add_travel_distance,
    add_last_week_goals,
    add_last_week_behinds,
    add_last_week_result,
    add_last_week_score,
    add_cum_win_points,
    add_rolling_last_week_win_rate,
    add_win_streak,
]
DATA_TRANSFORMERS: List[FeatureFunctionType] = [
    TeamDataStacker(index_cols=INDEX_COLS).transform,
    FeatureBuilder(feature_funcs=FEATURE_FUNCS).transform,
    OppoFeatureBuilder(
        match_cols=[
            "team",
            "year",
            "round_number",
            "score",
            "oppo_score",
            "out_of_state",
            "at_home",
            "oppo_team",
            "venue",
            "round_type",
        ]
    ).transform,
    # Features dependent on oppo columns
    FeatureBuilder(feature_funcs=[add_cum_percent, add_ladder_position]).transform,
]
DATA_READERS: List[Callable] = [FitzroyDataReader().match_results]
MODEL_ESTIMATORS = (StandardScaler(), XGBRegressor())

np.random.seed(42)


class MatchModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on match data"""

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = MODEL_ESTIMATORS,
        name: Optional[str] = None,
        module_name: str = "",
    ) -> None:
        super().__init__(estimators=estimators, name=name, module_name=module_name)


class MatchModelData:
    """Load and clean data for the XGB pipeline.

    Args:
        data_transformers (list[callable]): Functions that receive, transform,
            and return data frames.
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
        data_transformers: List[FeatureFunctionType] = DATA_TRANSFORMERS,
        train_years: YearsType = (None, 2015),
        test_years: YearsType = (2016, 2016),
    ) -> None:
        self._train_years = train_years
        self._test_years = test_years

        # Need to reverse the transformation steps, because composition makes the output
        # of each new function the argument for the previous
        compose_all = reduce(
            self.__compose_two, reversed(data_transformers), lambda x: x
        )

        data_frame = (
            data_readers[0]()
            .rename(columns=COL_TRANSLATIONS)
            .astype({"year": int})
            .drop(["round", "game", "date"], axis=1)
        )

        # There was some sort of round-robin finals round in 1897 and figuring out
        # a way to clean it up that makes sense is more trouble than just dropping a few rows
        data_frame = data_frame[
            (data_frame["year"] != 1897) | (data_frame["round_number"] != 15)
        ]

        self.data = compose_all(data_frame).drop("venue", axis=1).dropna()

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
    def __compose_two(
        composed_func: FeatureFunctionType, func_element: FeatureFunctionType
    ) -> FeatureFunctionType:
        return lambda x: composed_func(func_element(x))

    @staticmethod
    def __y(data_frame: pd.DataFrame) -> pd.Series:
        return data_frame["score"] - data_frame["oppo_score"]
