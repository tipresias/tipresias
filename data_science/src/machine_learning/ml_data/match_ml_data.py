"""Module with wrapper class for XGBoost model and its associated data class"""

from typing import List, Callable
from datetime import datetime, date
import pandas as pd

from machine_learning.types import DataFrameTransformer, YearPair, DataReadersParam
from machine_learning.data_processors import (
    TeamDataStacker,
    FeatureBuilder,
    OppoFeatureBuilder,
)
from machine_learning.data_processors.feature_functions import (
    add_result,
    add_margin,
    add_cum_percent,
    add_cum_win_points,
    add_ladder_position,
    add_win_streak,
    add_out_of_state,
    add_travel_distance,
    add_elo_rating,
    add_elo_pred_win,
    add_shifted_team_features,
)
from machine_learning.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
    calculate_division,
    calculate_rolling_mean_by_dimension,
)
from machine_learning.data_transformation.data_cleaning import clean_match_data
from machine_learning.data_import import FitzroyDataImporter
from machine_learning.ml_data import BaseMLData
from machine_learning.data_config import INDEX_COLS
from machine_learning.utils import DataTransformerMixin
from machine_learning.settings import MELBOURNE_TIMEZONE


FEATURE_FUNCS: List[DataFrameTransformer] = [
    add_out_of_state,
    add_travel_distance,
    add_result,
    add_margin,
    add_shifted_team_features(
        shift_columns=[
            "score",
            "oppo_score",
            "result",
            "margin",
            "team_goals",
            "team_behinds",
        ]
    ),
    add_cum_win_points,
    add_win_streak,
    feature_calculator(
        [
            (calculate_rolling_rate, [("prev_match_result",)]),
            (
                calculate_rolling_mean_by_dimension,
                [
                    ("oppo_team", "margin"),
                    ("oppo_team", "result"),
                    ("oppo_team", "score"),
                    ("venue", "margin"),
                    ("venue", "result"),
                    ("venue", "score"),
                ],
            ),
        ]
    ),
]
DATA_TRANSFORMERS: List[DataFrameTransformer] = [
    # add_elo_rating depends on DF still being organized per-match
    # with home_team/away_team columns
    FeatureBuilder(
        index_cols=["home_team", "year", "round_number"], feature_funcs=[add_elo_rating]
    ).transform,
    TeamDataStacker(index_cols=INDEX_COLS).transform,
    FeatureBuilder(feature_funcs=FEATURE_FUNCS).transform,
    OppoFeatureBuilder(
        match_cols=[
            "team",
            "year",
            "round_number",
            "score",
            "oppo_score",
            "team_goals",
            "oppo_team_goals",
            "team_behinds",
            "oppo_team_behinds",
            # TODO: I have to omit these columns, because I accidentally left them in
            # when building betting features, and I need the columns to be the same
            # in order not to retrain my saved models.
            # "result",
            # "oppo_result",
            "margin",
            "oppo_margin",
            "elo_rating",
            "oppo_elo_rating",
            "out_of_state",
            "at_home",
            "oppo_team",
            "venue",
            "round_type",
            "date",
        ]
    ).transform,
    # Features dependent on oppo columns
    FeatureBuilder(
        feature_funcs=[
            add_cum_percent,
            add_ladder_position,
            add_elo_pred_win,
            feature_calculator(
                [
                    (calculate_rolling_rate, [("elo_pred_win",)]),
                    (calculate_division, [("elo_rating", "ladder_position")]),
                ]
            ),
        ]
    ).transform,
    OppoFeatureBuilder(oppo_feature_cols=["cum_percent", "ladder_position"]).transform,
]
DATA_READERS: DataReadersParam = {
    "match": (FitzroyDataImporter().match_results, {}),
    "fixture": (FitzroyDataImporter().fetch_fixtures, {}),
}


class MatchMLData(BaseMLData, DataTransformerMixin):
    """Load and clean match data"""

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
        self.right_now = datetime.now(tz=MELBOURNE_TIMEZONE)
        self.current_year = self.right_now.year
        self.data_readers = data_readers
        self._data = None
        self.fetch_data = fetch_data
        self.index_cols = index_cols

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
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

            if self.fetch_data and "fixture" in self.data_readers.keys():
                fixture_data_reader, _ = self.data_readers["fixture"]
                fixture_data = self.__fetch_fixture_data(fixture_data_reader)
            else:
                fixture_data = None

            self._data = (
                self._compose_transformers(  # pylint: disable=E1102
                    clean_match_data(match_data, fixture_data)
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

    def __fetch_fixture_data(self, data_reader: Callable) -> pd.DataFrame:
        fixture_data_frame = data_reader(
            start_date=f"{self.current_year}-01-01",
            end_date=f"{self.current_year}-12-31",
        )

        latest_match_date = fixture_data_frame["date"].max()

        if self.right_now > latest_match_date:
            print(
                f"No unplayed matches found in {self.current_year}. We will try to fetch "
                f"fixture for {self.current_year + 1}.\n"
            )

            fixture_data_frame = data_reader(
                start_date=f"{self.current_year + 1}-01-01",
                end_date=f"{self.current_year + 1}-12-31",
            )

            latest_match_date = fixture_data_frame["date"].max()

            if self.right_now > latest_match_date:
                raise ValueError(
                    f"No unplayed matches found in {self.current_year + 1}, and we're not going "
                    "to keep trying. Please try a season that hasn't been completed.\n"
                )

        return fixture_data_frame
