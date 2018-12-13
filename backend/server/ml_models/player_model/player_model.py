"""Model class trained on player data and its associated data class"""

from typing import List, Tuple, Union, Sequence, Callable, Optional
from functools import reduce
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator
from xgboost import XGBRegressor

from server.types import FeatureFunctionType, YearsType
from server.data_processors import (
    FeatureBuilder,
    PlayerDataStacker,
    PlayerDataAggregator,
    OppoFeatureBuilder,
)
from server.data_processors.feature_functions import (
    add_last_year_brownlow_votes,
    add_rolling_player_stats,
    add_cum_matches_played,
)
from server.data_processors import FitzroyDataReader
from server.ml_models.ml_model import MLModel

MATCH_STATS_COLS = [
    "at_home",
    "score",
    "oppo_score",
    "team",
    "oppo_team",
    "year",
    "round_number",
]
COL_TRANSLATIONS = {
    "season": "year",
    "time_on_ground__": "time_on_ground",
    "id": "player_id",
    "game": "match_id",
}
FEATURE_FUNCS: Sequence[FeatureFunctionType] = [
    add_last_year_brownlow_votes,
    add_rolling_player_stats,
    add_cum_matches_played,
]
DATA_TRANSFORMERS: List[FeatureFunctionType] = [
    PlayerDataStacker().transform,
    FeatureBuilder(
        feature_funcs=FEATURE_FUNCS,
        index_cols=["team", "year", "round_number", "player_id"],
    ).transform,
    PlayerDataAggregator().transform,
    OppoFeatureBuilder(match_cols=MATCH_STATS_COLS).transform,
]

fitzroy = FitzroyDataReader()
DATA_READERS: List[Callable] = [fitzroy.get_afltables_stats, fitzroy.match_results]
MODEL_ESTIMATORS = (StandardScaler(), XGBRegressor())

np.random.seed(42)


class PlayerModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on player data"""

    def __init__(
        self,
        estimators: Sequence[BaseEstimator] = MODEL_ESTIMATORS,
        name: Optional[str] = None,
        module_name: str = "",
    ) -> None:
        super().__init__(estimators=estimators, name=name, module_name=module_name)


class PlayerModelData:
    """Load and clean data for the XGBRegressor pipeline.

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
        start_date="1965-01-01",
        end_date="2016-12-31",
    ) -> None:
        self._train_years = train_years
        self._test_years = test_years

        # Need to reverse the transformation steps, because composition makes the output
        # of each new function the argument for the previous
        compose_all = reduce(
            self.__compose_two, reversed(data_transformers), lambda x: x
        )

        data_frame = (
            data_readers[0](start_date=start_date, end_date=end_date)
            # Some player data venues have trailing spaces
            .assign(venue=lambda x: x["venue"].str.strip())
            # Player data match IDs are wrong for recent years.
            # The easiest way to add correct ones is to graft on the IDs
            # from match_results. Also, match_results round_numbers are more useful.
            .merge(
                data_readers[1]()[["date", "venue", "round_number", "game"]],
                on=["date", "venue"],
                how="left",
            )
            # As of 11-10-2018, match_results is still missing finals data from 2018.
            # Joining on date/venue leaves two duplicates played at M.C.G.
            # on 29-4-1986 & 9-8-1986, but that's an acceptable loss of data
            # and easier than munging team names
            .dropna()
            .rename(columns=COL_TRANSLATIONS)
            .astype({"year": int, "match_id": int})
            .assign(
                player_name=lambda x: x["first_name"] + " " + x["surname"],
                # Need to add year to ID, because there are some
                # player_id/match_id combos, decades apart, that by chance overlap
                id=self.__id_col,
            )
            .drop(
                [
                    "first_name",
                    "surname",
                    "round",
                    "local_start_time",
                    "attendance",
                    "hq1g",
                    "hq1b",
                    "hq2g",
                    "hq2b",
                    "hq3g",
                    "hq3b",
                    "hq4g",
                    "hq4b",
                    "aq1g",
                    "aq1b",
                    "aq2g",
                    "aq2b",
                    "aq3g",
                    "aq3b",
                    "aq4g",
                    "aq4b",
                    "jumper_no_",
                    "umpire_1",
                    "umpire_2",
                    "umpire_3",
                    "umpire_4",
                    "substitute",
                    "group_id",
                    "date",
                    "venue",
                ],
                axis=1,
            )
            # Some early matches (1800s) have fully-duplicated rows
            .drop_duplicates()
            .set_index("id")
            .sort_index()
        )

        # Drawn finals get replayed, which screws up my indexing and a bunch of other
        # data munging, so getting match_ids for the repeat matches, and filtering
        # them out of the data frame
        duplicate_matches = data_frame[
            data_frame.duplicated(
                subset=["year", "round_number", "player_id"], keep="last"
            )
        ]["match_id"]

        # There were some weird round-robin rounds in the early days, and it's easier to
        # drop them rather than figure out how to split up the rounds.
        data_frame = data_frame[
            ((data_frame["year"] != 1897) | (data_frame["round_number"] != 15))
            & ((data_frame["year"] != 1924) | (data_frame["round_number"] != 19))
            & (~data_frame["match_id"].isin(duplicate_matches))
        ]

        self.data = compose_all(data_frame).dropna()

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

    @staticmethod
    def __id_col(df):
        return (
            df["player_id"].astype(str)
            + df["match_id"].astype(str)
            + df["year"].astype(str)
        )
