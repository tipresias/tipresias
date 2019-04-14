"""Module for machine learning data class that joins various data sources together"""

from typing import List, Optional
from datetime import date
import pandas as pd

from machine_learning.data_processors import FeatureBuilder
from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_division,
    calculate_multiplication,
)
from machine_learning.types import YearPair, DataFrameTransformer, DataReadersParam
from machine_learning.utils import DataTransformerMixin
from machine_learning.data_config import CATEGORY_COLS
from machine_learning.data_import import (
    FitzroyDataImporter,
    FootywireDataImporter,
    afl_data_importer,
)
from machine_learning.data_transformation.data_cleaning import clean_joined_data
from . import BaseMLData


DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    FeatureBuilder(
        feature_funcs=[
            feature_calculator(
                [
                    (calculate_division, [("elo_rating", "win_odds")]),
                    (calculate_multiplication, [("win_odds", "ladder_position")]),
                ]
            )
        ]
    ).transform
]
DATA_READERS: DataReadersParam = {
    # Defaulting to start_date as the 1965 season, because earlier seasons don't
    # have much in the way of player stats, just goals and behinds, which we
    # already have at the team level.
    "player": (
        FitzroyDataImporter.get_afltables_stats,
        {"start_date": "1965-01-01", "end_date": str(date.today())},
    ),
    "match": (FitzroyDataImporter().match_results, {}),
    "betting": (FootywireDataImporter().get_betting_odds, {}),
    "fixture": (FootywireDataImporter().get_fixture, {}),
    "roster": (afl_data_importer.get_rosters, {}),
}


class JoinedMLData(BaseMLData, DataTransformerMixin):
    """Load and clean data from all data sources"""

    def __init__(
        self,
        data_readers: DataReadersParam = DATA_READERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        category_cols: List[str] = CATEGORY_COLS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        fetch_data: bool = False,
    ) -> None:
        super().__init__(
            train_years=train_years, test_years=test_years, fetch_data=fetch_data
        )

        self._data_transformers = data_transformers + [self.__sort_data_frame_columns]
        self.data_readers = data_readers
        self._data = None
        self.category_cols = category_cols

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            player_data_reader, player_data_kwargs = self.data_readers["player"]
            match_data_reader, match_data_kwargs = self.data_readers["match"]
            betting_data_reader, betting_data_kwargs = self.data_readers["betting"]

            player_data = player_data_reader(**player_data_kwargs)
            match_data = match_data_reader(
                **{**match_data_kwargs, **{"fetch_data": self.fetch_data}}
            )
            betting_data = betting_data_reader(
                **{**betting_data_kwargs, **{"fetch_data": self.fetch_data}}
            )

            data_frame = clean_joined_data(
                player_data,
                match_data,
                betting_data,
                fixture_data=self.__fixture_data,
                roster_data=self.__roster_data,
            )

            self._data = (
                self._compose_transformers(data_frame)  # pylint: disable=E1102
                .dropna()
                .sort_index()
            )

            # # For some reason the 'date' column in MatchMLData gets converted from 'datetime64'
            # # to 'object' as part of the concatenation process.
            # if "date" in self._data.columns:
            #     self._data.loc[:, "date"] = self._data["date"].pipe(pd.to_datetime)

        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    @property
    def __fixture_data(self) -> Optional[pd.DataFrame]:
        if self.fetch_data and "fixture" in self.data_readers.keys():
            fixture_data_reader, fixture_data_kwargs = self.data_readers["fixture"]
            return fixture_data_reader(**fixture_data_kwargs)

        return None

    @property
    def __roster_data(self) -> Optional[pd.DataFrame]:
        if self.fetch_data and "roster" in self.data_readers.keys():
            roster_data_reader, roster_data_kwargs = self.data_readers["roster"]
            return roster_data_reader(**roster_data_kwargs)

        return None

    def __sort_data_frame_columns(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        numeric_data_frame = data_frame.select_dtypes(include="number").fillna(0)

        if self.category_cols is None:
            category_data_frame = data_frame.drop(numeric_data_frame.columns, axis=1)
        else:
            category_data_frame = data_frame[self.category_cols]

        return pd.concat([category_data_frame, numeric_data_frame], axis=1)
