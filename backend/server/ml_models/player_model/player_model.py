"""Model class trained on player data and its associated data class"""

from typing import List, Callable, Optional
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import make_pipeline, Pipeline
from xgboost import XGBRegressor

from server.types import DataFrameTransformer, YearPair
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
from server.data_processors.feature_calculation import (
    feature_calculator,
    calculate_division,
    calculate_addition,
)
from server.data_readers import FitzroyDataReader
from server.ml_models.ml_model import MLModel, MLModelData, DataTransformerMixin
from server.ml_models.data_config import TEAM_NAMES, SEED, INDEX_COLS

MATCH_STATS_COLS = [
    "at_home",
    "score",
    "oppo_score",
    "team",
    "oppo_team",
    "year",
    "round_number",
]
DROPPABLE_COLS = [
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
]
COL_TRANSLATIONS = {
    "season": "year",
    "time_on_ground__": "time_on_ground",
    "id": "player_id",
    "game": "match_id",
}

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

fitzroy = FitzroyDataReader()
DATA_READERS: List[Callable] = [fitzroy.get_afltables_stats, fitzroy.match_results]
PIPELINE = make_pipeline(
    ColumnTransformer(
        [
            (
                "onehotencoder",
                OneHotEncoder(categories=[TEAM_NAMES, TEAM_NAMES], sparse=False),
                ["team", "oppo_team"],
            )
        ],
        remainder="passthrough",
    ),
    StandardScaler(),
    XGBRegressor(),
)

np.random.seed(SEED)


class PlayerModel(MLModel):
    """Create pipeline for fitting/predicting with model trained on player data"""

    def __init__(
        self, pipeline: Pipeline = PIPELINE, name: Optional[str] = None
    ) -> None:
        super().__init__(pipeline=pipeline, name=name)


class PlayerModelData(MLModelData, DataTransformerMixin):
    """Load and clean player data"""

    def __init__(
        self,
        data_readers: List[Callable] = DATA_READERS,
        data_transformers: List[DataFrameTransformer] = DATA_TRANSFORMERS,
        train_years: YearPair = (None, 2015),
        test_years: YearPair = (2016, 2016),
        start_date="1965-01-01",
        end_date="2016-12-31",
        index_cols: List[str] = INDEX_COLS,
    ) -> None:
        super().__init__(train_years=train_years, test_years=test_years)

        self._data_transformers = data_transformers

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
            .drop(DROPPABLE_COLS, axis=1)
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

        self._data = (
            self._compose_transformers(data_frame)  # pylint: disable=E1102
            .fillna(0)
            .set_index(index_cols, drop=False)
            .rename_axis([None] * len(index_cols))
            .sort_index()
        )

    @property
    def data(self):
        return self._data

    @property
    def data_transformers(self):
        return self._data_transformers

    @staticmethod
    def __id_col(data_frame):
        return (
            data_frame["player_id"].astype(str)
            + data_frame["match_id"].astype(str)
            + data_frame["year"].astype(str)
        )
