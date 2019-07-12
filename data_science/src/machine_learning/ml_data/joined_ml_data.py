"""Module for machine learning data class that joins various data sources together"""

from typing import List, Dict
from datetime import date
import pandas as pd

from machine_learning.data_processors import FeatureBuilder
from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_division,
    calculate_multiplication,
)
from machine_learning.types import YearPair, DataFrameTransformer, CalculatorPair
from machine_learning.utils import DataTransformerMixin
from machine_learning.data_config import CATEGORY_COLS, ORIGINAL_COLUMNS
from machine_learning.data_transformation import data_cleaning
from machine_learning.ml_data import PlayerMLData, MatchMLData, BettingMLData
from . import BaseMLData

MATCH_STATS_COLS = [
    "team",
    "year",
    "round_number",
    "score",
    "oppo_score",
    "goals",
    "oppo_goals",
    "behinds",
    "oppo_behinds",
    "result",
    "oppo_result",
    "margin",
    "oppo_margin",
    "out_of_state",
    "at_home",
    "oppo_team",
    "venue",
    "round_type",
    "date",
]

FEATURE_CALCS: List[CalculatorPair] = [
    (calculate_division, [("elo_rating", "win_odds")]),
    (calculate_multiplication, [("win_odds", "ladder_position")]),
]

FEATURE_FUNCS: List[DataFrameTransformer] = [feature_calculator(FEATURE_CALCS)]

DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    data_cleaning.clean_joined_data,
    FeatureBuilder(
        feature_funcs=FEATURE_FUNCS, index_cols=["team", "year", "round_number"]
    ).transform,
]

DATA_READERS: Dict[str, BaseMLData] = {
    # Defaulting to start_date as the 1965 season, because earlier seasons don't
    # have much in the way of player stats, just goals and behinds, which we
    # already have at the team level.
    "player": PlayerMLData(start_date="1965-01-01"),
    "match": MatchMLData(),
    "betting": BettingMLData(),
}


class JoinedMLData(BaseMLData, DataTransformerMixin):
    """Load and clean data from all data sources"""

    def __init__(
        self,
        data_readers: Dict[str, BaseMLData] = DATA_READERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        category_cols: List[str] = CATEGORY_COLS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        fetch_data: bool = False,
        start_date: str = "1897-01-01",
        end_date: str = str(date.today()),
    ) -> None:
        super().__init__(
            train_years=train_years,
            test_years=test_years,
            fetch_data=fetch_data,
            start_date=start_date,
            end_date=end_date,
        )

        self._data_transformers = data_transformers
        self.data_readers = data_readers
        self._data = None
        self.category_cols = category_cols

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            self.data_readers["player"].fetch_data = self.fetch_data
            # TODO: We don't wan to overwrite player data start date when training,
            # because the original model was trained on data starting in 1965
            # Allow for MLData to pass params to data readers to remedy this
            self.data_readers["player"].start_date = self.start_date
            self.data_readers["player"].end_date = self.end_date
            player_data = self.data_readers["player"].data

            self.data_readers["match"].fetch_data = self.fetch_data
            self.data_readers["match"].start_date = self.start_date
            self.data_readers["match"].end_date = self.end_date
            match_data = self.data_readers["match"].data

            self.data_readers["betting"].fetch_data = self.fetch_data
            self.data_readers["betting"].start_date = self.start_date
            self.data_readers["betting"].end_date = self.end_date
            # Betting data dates are correct, but the times are arbitrarily set by the
            # parser, so better to leave the date definition to a different data source
            betting_data = self.data_readers["betting"].data.drop("date", axis=1)

            self._data = (
                self._compose_transformers(  # pylint: disable=E1102
                    [player_data, match_data, betting_data]
                )
                .pipe(self.__sort_data_frame_columns)
                .dropna()
                .sort_index()
                # TODO: This is only a temporary renaming to keep column names
                # consistent with saved models in order to avoid having to retrain them
                .rename(columns=lambda col: col.replace("team_goals", "goals"))
                .rename(columns=lambda col: col.replace("team_behinds", "behinds"))
                # TODO: The data refactor reordered the columns, which completely
                # messed up predictions. I don't want to retrain the models, so I'll
                # just use the original column list to make sure they're in the same
                # order as before, and figure out a better solution later
                .loc[:, ORIGINAL_COLUMNS]
            )

        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    def __sort_data_frame_columns(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        numeric_data_frame = data_frame.select_dtypes(include="number").fillna(0)

        if self.category_cols is None:
            category_data_frame = data_frame.drop(numeric_data_frame.columns, axis=1)
        else:
            category_data_frame = data_frame[self.category_cols]

        return pd.concat([category_data_frame, numeric_data_frame], axis=1)
