"""Model class trained on player data and its associated data class"""

from typing import List, Optional
from datetime import date
import pandas as pd

from machine_learning.types import DataFrameTransformer, YearPair, DataReadersParam
from machine_learning.data_processors import (
    FeatureBuilder,
    PlayerDataStacker,
    PlayerDataAggregator,
    OppoFeatureBuilder,
)
from machine_learning.data_processors.feature_functions import (
    add_last_year_brownlow_votes,
    add_rolling_player_stats,
    add_cum_matches_played,
)
from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_division,
    calculate_addition,
)
from machine_learning.data_import import FitzroyDataImporter, AflDataImporter
from machine_learning.data_transformation.data_cleaning import clean_player_data
from machine_learning.ml_data import BaseMLData
from machine_learning.data_config import INDEX_COLS
from machine_learning.utils import DataTransformerMixin

MATCH_STATS_COLS = [
    "at_home",
    "score",
    "oppo_score",
    "team",
    "oppo_team",
    "year",
    "round_number",
    "date",
]

FEATURE_FUNCS: List[DataFrameTransformer] = [
    add_last_year_brownlow_votes,
    add_rolling_player_stats,
    add_cum_matches_played,
    feature_calculator(
        [
            (
                calculate_addition,
                [("rolling_prev_match_goals", "rolling_prev_match_behinds")],
            )
        ]
    ),
    feature_calculator(
        [
            (
                calculate_division,
                [
                    (
                        "rolling_prev_match_goals",
                        "rolling_prev_match_goals_plus_rolling_prev_match_behinds",
                    )
                ],
            )
        ]
    ),
]
DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    PlayerDataStacker().transform,
    FeatureBuilder(
        feature_funcs=FEATURE_FUNCS,
        index_cols=["team", "year", "round_number", "player_id"],
    ).transform,
    PlayerDataAggregator(aggregations=["sum", "max", "min", "skew", "std"]).transform,
    OppoFeatureBuilder(match_cols=MATCH_STATS_COLS).transform,
]

fitzroy = FitzroyDataImporter()
afl = AflDataImporter()
DATA_READERS: DataReadersParam = {
    "player": (
        fitzroy.get_afltables_stats,
        # Defaulting to start_date as the 1965 season, because earlier seasons don't
        # have much in the way of player stats, just goals and behinds, which we
        # already have at the team level.
        {"start_date": "1965-01-01", "end_date": str(date.today())},
    ),
    "match": (fitzroy.match_results, {}),
    "roster": (afl.fetch_rosters, {}),
}


class PlayerMLData(BaseMLData, DataTransformerMixin):
    """Load and clean player data"""

    def __init__(
        self,
        data_readers: DataReadersParam = DATA_READERS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        index_cols: List[str] = INDEX_COLS,
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
        self.fetch_data = fetch_data
        self.index_cols = index_cols

    @property
    def data(self):
        if self._data is None:
            player_data_reader, player_data_kwargs = self.data_readers["player"]
            player_data = player_data_reader(
                **{
                    **player_data_kwargs,
                    **{"start_date": self.start_date, "end_date": self.end_date},
                }
            )

            match_data_reader, match_data_kwargs = self.data_readers["match"]
            match_data = match_data_reader(
                **{
                    **match_data_kwargs,
                    **{
                        "fetch_data": self.fetch_data,
                        "start_date": self.start_date,
                        "end_date": self.end_date,
                    },
                }
            )
            roster_data = self.__roster_data(match_data)

            self._data = (
                self._compose_transformers(  # pylint: disable=E1102
                    clean_player_data(player_data, match_data, roster_data=roster_data)
                )
                .fillna(0)
                .set_index(self.index_cols, drop=False)
                .rename_axis([None] * len(self.index_cols))
                .sort_index()
            )

        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    def __roster_data(self, match_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        if self.fetch_data and "roster" in self.data_readers.keys():
            current_year = date.today().year
            round_number = self.__upcoming_round_number(match_data, current_year)
            roster_data_reader, roster_data_kwargs = self.data_readers["roster"]
            return roster_data_reader(round_number, **{**roster_data_kwargs})

        return None

    @staticmethod
    def __upcoming_round_number(match_data: pd.DataFrame, current_year: int) -> int:
        if match_data["season"].max() == current_year:
            return match_data.query("season == @current_year")["round_number"].max() + 1

        return 1
