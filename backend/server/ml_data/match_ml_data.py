"""Module with wrapper class for XGBoost model and its associated data class"""

from typing import List, Callable, Any, Pattern
import re
from datetime import datetime, timezone
import pandas as pd

from server.types import DataFrameTransformer, YearPair
from server.data_processors import TeamDataStacker, FeatureBuilder, OppoFeatureBuilder
from server.data_processors.feature_functions import (
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
from server.data_processors.feature_calculation import (
    feature_calculator,
    calculate_rolling_rate,
    calculate_division,
    calculate_rolling_mean_by_dimension,
)
from server.data_readers import FitzroyDataReader, FootywireDataReader
from server.ml_data import BaseMLData
from server.data_config import INDEX_COLS, FOOTYWIRE_VENUE_TRANSLATIONS
from server.utils import DataTransformerMixin

COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
REGULAR_ROUND: Pattern = re.compile(r"round\s+(\d+)$", flags=re.I)

FEATURE_FUNCS: List[DataFrameTransformer] = [
    add_out_of_state,
    add_travel_distance,
    add_result,
    add_margin,
    add_shifted_team_features(
        shift_columns=["score", "oppo_score", "result", "margin", "goals", "behinds"]
    ),
    add_cum_win_points,
    add_win_streak,
    add_elo_rating,
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
    TeamDataStacker(index_cols=INDEX_COLS).transform,
    FeatureBuilder(feature_funcs=FEATURE_FUNCS).transform,
    OppoFeatureBuilder(
        match_cols=[
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
DATA_READERS: List[Callable] = [
    FitzroyDataReader().match_results,
    FootywireDataReader().get_fixture,
]


class MatchMLData(BaseMLData, DataTransformerMixin):
    """Load and clean match data"""

    def __init__(
        self,
        data_readers: List[Callable] = DATA_READERS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        index_cols: List[str] = INDEX_COLS,
        fetch_data: bool = False,
    ) -> None:
        super().__init__(
            train_years=train_years, test_years=test_years, fetch_data=fetch_data
        )

        self._data_transformers = data_transformers
        self.right_now = datetime.now(tz=timezone.utc)
        self.current_year = self.right_now.year

        data_frame = (
            data_readers[0](fetch_data=fetch_data)
            .rename(columns=COL_TRANSLATIONS)
            # fitzRoy returns integers that represent some sort of datetime, and the only
            # way to parse them is converting them to dates.
            # NOTE: If the matches parsed only go back to 1990 (give or take, I can't remember)
            # you can parse the date integers into datetime
            .assign(date=lambda df: pd.to_datetime(df["date"], unit="D"))
            .astype({"year": int})
            .drop(["round", "game"], axis=1)
        )

        # There were some weird round-robin rounds in the early days, and it's easier to
        # drop them rather than figure out how to split up the rounds.
        data_frame = data_frame[
            ((data_frame["year"] != 1897) | (data_frame["round_number"] != 15))
            & ((data_frame["year"] != 1924) | (data_frame["round_number"] != 19))
        ]

        if fetch_data and len(data_readers) > 1:
            fixture_data_frame = self.__fetch_fixture_data(data_readers[1])
            fixture_rounds = fixture_data_frame["round"]
            upcoming_round = fixture_rounds[
                fixture_data_frame["date"] > self.right_now
            ].min()

            upcoming_fixture_data_frame = (
                fixture_data_frame.assign(round_type=self.__round_type_column)
                .loc[
                    fixture_data_frame["round"] == upcoming_round,
                    [
                        "date",
                        "venue",
                        "season",
                        "round",
                        "home_team",
                        "away_team",
                        "round_type",
                    ],
                ]
                .rename(columns={"round": "round_number", "season": "year"})
                .assign(venue=lambda df: df["venue"].map(self.__map_footywire_venues))
            )

            data_frame = (
                pd.concat([data_frame, upcoming_fixture_data_frame], sort=False)
                .reset_index(drop=True)
                .drop_duplicates(
                    subset=[
                        "date",
                        "venue",
                        "year",
                        "round_number",
                        "home_team",
                        "away_team",
                    ]
                )
                .fillna(0)
            )

        self._data = (
            self._compose_transformers(data_frame)  # pylint: disable=E1102
            .fillna(0)
            .set_index(index_cols, drop=False)
            .rename_axis([None] * len(index_cols))
            .sort_index()
        )

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    def __fetch_fixture_data(self, data_reader: Any) -> pd.DataFrame:
        fixture_data_frame = data_reader(
            year_range=(self.current_year, self.current_year + 1),
            fetch_data=self.fetch_data,
        ).assign(date=lambda df: df["date"].dt.tz_localize(timezone.utc))

        latest_match_date = fixture_data_frame["date"].max()

        if self.right_now > latest_match_date:
            print(
                f"No unplayed matches found in {self.current_year}. We will try to fetch "
                f"fixture for {self.current_year + 1}.\n"
            )

            fixture_data_frame = data_reader(
                year_range=(self.current_year + 1, self.current_year + 2),
                fetch_data=self.fetch_data,
            ).assign(date=lambda df: df["date"].dt.tz_localize(timezone.utc))
            latest_match_date = fixture_data_frame["date"].max()

            if self.right_now > latest_match_date:
                raise ValueError(
                    f"No unplayed matches found in {self.current_year + 1}, and we're not going "
                    "to keep trying. Please try a season that hasn't been completed.\n"
                )

        return fixture_data_frame

    @staticmethod
    def __map_footywire_venues(venue: str) -> str:
        if venue not in FOOTYWIRE_VENUE_TRANSLATIONS.keys():
            return venue

        return FOOTYWIRE_VENUE_TRANSLATIONS[venue]

    @staticmethod
    def __round_type_column(data_frame: pd.DataFrame) -> pd.DataFrame:
        return data_frame["round_label"].map(
            lambda label: "Finals"
            if re.search(REGULAR_ROUND, label) is None
            else "Regular"
        )
