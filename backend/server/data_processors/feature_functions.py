"""Module for functions that add features to data frames via FeatureBuilder.

All functions have the following signature:

Args:
    data_frame (pandas.DataFrame): Data frame to be transformed.

Returns:
    pandas.DataFrame
"""

from typing import List, Tuple, Optional
import math
from functools import partial, reduce
import pandas as pd
import numpy as np

from server.ml_models.data_config import INDEX_COLS, CITIES, TEAM_CITIES, VENUE_CITIES

TEAM_LEVEL = 0
YEAR_LEVEL = 1
ROUND_LEVEL = 2
REORDERED_TEAM_LEVEL = 2
REORDERED_YEAR_LEVEL = 0
REORDERED_ROUND_LEVEL = 1
WIN_POINTS = 4
EARTH_RADIUS = 6371

# Constants for ELO calculations
BASE_RATING = 1000
K = 35.6
X = 0.49
M = 130
# Home Ground Advantage
HGA = 9
S = 250
CARRYOVER = 0.575


EloIndexType = Tuple[int, int, str]


def add_result(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's match result (win, draw, loss) as float"""

    if "score" not in data_frame.columns or "oppo_score" not in data_frame.columns:
        raise ValueError(
            "To calculate match result, 'score' and 'oppo_score' "
            "must be in the data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    wins = (data_frame["score"] > data_frame["oppo_score"]).astype(int)
    draws = (data_frame["score"] == data_frame["oppo_score"]).astype(int) * 0.5

    return data_frame.assign(result=wins + draws)


def add_margin(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's margin from the match"""

    if "score" not in data_frame.columns or "oppo_score" not in data_frame.columns:
        raise ValueError(
            "To calculate margin, 'score' and 'oppo_score' "
            "must be in the data frame, but the columns given "
            f"were {data_frame.columns}"
        )

    return data_frame.assign(margin=data_frame["score"] - data_frame["oppo_score"])


def add_cum_percent(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's cumulative percent (cumulative score / cumulative opponents' score)"""

    if (
        "prev_match_score" not in data_frame.columns
        or "prev_match_oppo_score" not in data_frame.columns
    ):
        raise ValueError(
            "To calculate cum percent, 'prev_match_score' and "
            "'prev_match_oppo_score' must be in the data frame, "
            f"but the columns given were {data_frame.columns}"
        )

    cum_score = (
        data_frame["prev_match_score"].groupby(level=[TEAM_LEVEL, YEAR_LEVEL]).cumsum()
    )
    cum_oppo_score = (
        data_frame["prev_match_oppo_score"]
        .groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
        .cumsum()
    )

    return data_frame.assign(cum_percent=cum_score / cum_oppo_score)


def add_cum_win_points(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's cumulative win points (based on cumulative result)"""

    if "prev_match_result" not in data_frame.columns:
        raise ValueError(
            "To calculate cumulative win points, 'prev_match_result' "
            "must be in the data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    cum_win_points_col = (
        (data_frame["prev_match_result"] * WIN_POINTS)
        .groupby(level=[TEAM_LEVEL, YEAR_LEVEL])
        .cumsum()
    )

    return data_frame.assign(cum_win_points=cum_win_points_col)


def add_betting_pred_win(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add whether a team is predicted to win per the betting odds"""

    odds_cols = ["win_odds", "oppo_win_odds", "line_odds", "oppo_line_odds"]

    if any((odds_col not in data_frame.columns for odds_col in odds_cols)):
        raise ValueError(
            f"To calculate betting predicted win, all odds columns ({odds_cols})"
            "must be in data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    is_favoured = (
        (data_frame["win_odds"] < data_frame["oppo_win_odds"])
        | (data_frame["line_odds"] < data_frame["oppo_line_odds"])
    ).astype(int)
    odds_are_even = (
        (data_frame["win_odds"] == data_frame["oppo_win_odds"])
        & (data_frame["line_odds"] == data_frame["oppo_line_odds"])
    ).astype(int)

    # Give half point for predicted draws
    predicted_results = is_favoured + (odds_are_even * 0.5)

    return data_frame.assign(betting_pred_win=predicted_results)


def add_elo_pred_win(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add whether a team is predicted to win per elo ratings"""

    if (
        "elo_rating" not in data_frame.columns
        or "oppo_elo_rating" not in data_frame.columns
    ):
        raise ValueError(
            f"To calculate ELO predicted win, 'elo_rating' and 'oppo_elo_rating "
            "must be in data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    is_favoured = (data_frame["elo_rating"] > data_frame["oppo_elo_rating"]).astype(int)
    are_even = (data_frame["elo_rating"] == data_frame["oppo_elo_rating"]).astype(int)

    # Give half point for predicted draws
    predicted_results = is_favoured + (are_even * 0.5)

    return data_frame.assign(elo_pred_win=predicted_results)


def add_ladder_position(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's current ladder position (based on cumulative win points and percent)"""

    required_cols = INDEX_COLS + ["cum_win_points", "cum_percent"]

    if any((req_col not in data_frame.columns for req_col in required_cols)):
        raise ValueError(
            f"To calculate ladder position, all required columns ({required_cols})"
            "must be in the data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    # Pivot to get round-by-round match points and cumulative percent
    ladder_pivot_table = data_frame[
        INDEX_COLS + ["cum_win_points", "cum_percent"]
    ].pivot_table(
        index=["year", "round_number"],
        values=["cum_win_points", "cum_percent"],
        columns="team",
        aggfunc={"cum_win_points": np.sum, "cum_percent": np.mean},
    )

    # To get round-by-round ladder ranks, we sort each round by win points & percent,
    # then save index numbers
    ladder_index = []
    ladder_values = []

    for year_round_idx, round_row in ladder_pivot_table.iterrows():
        sorted_row = round_row.unstack(level=TEAM_LEVEL).sort_values(
            ["cum_win_points", "cum_percent"], ascending=False
        )

        for ladder_idx, team_name in enumerate(sorted_row.index.get_values()):
            ladder_index.append(tuple([team_name, *year_round_idx]))
            ladder_values.append(ladder_idx + 1)

    ladder_multi_index = pd.MultiIndex.from_tuples(
        ladder_index, names=tuple(INDEX_COLS)
    )
    ladder_position_col = pd.Series(
        ladder_values, index=ladder_multi_index, name="ladder_position"
    )

    return data_frame.assign(ladder_position=ladder_position_col)


# Calculate win/loss streaks. Positive result (win or draw) adds 1 (or 0.5);
# negative result subtracts 1. Changes in direction (i.e. broken streak) result in
# starting at 1 or -1.
def add_win_streak(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add a team's running win/loss streak through the end of the current match"""

    if "prev_match_result" not in data_frame.columns:
        raise ValueError(
            "To calculate win streak, 'prev_match_result' "
            "must be in data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    win_groups = data_frame["prev_match_result"].groupby(
        level=TEAM_LEVEL, group_keys=False
    )
    streak_groups = []

    for team_group_key, team_group in win_groups:
        streaks: List = []

        for idx, result in enumerate(team_group):
            # 1 represents win, 0.5 represents draw
            if result > 0:
                if idx == 0 or streaks[idx - 1] <= 0:
                    streaks.append(result)
                else:
                    streaks.append(streaks[idx - 1] + result)
            # 0 represents loss
            elif result == 0:
                if idx == 0 or streaks[idx - 1] >= 0:
                    streaks.append(-1)
                else:
                    streaks.append(streaks[idx - 1] - 1)
            elif result < 0:
                raise ValueError(
                    f"No results should be negative, but {result} "
                    f"is at index {idx} of group {team_group_key}"
                )
            else:
                # For a team's first match in the data set or any rogue NaNs, we add 0
                streaks.append(0)

        streak_groups.extend(streaks)

    return data_frame.assign(
        win_streak=pd.Series(streak_groups, index=data_frame.index)
    )


def add_out_of_state(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add whether a team is playing out of their home state."""

    if any([req_col not in data_frame.columns for req_col in ["venue", "team"]]):
        raise ValueError(
            "To calculate out of state matches, 'venue' and 'team' "
            "must be in the data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    venue_state = data_frame["venue"].map(lambda x: CITIES[VENUE_CITIES[x]]["state"])
    team_state = data_frame["team"].map(lambda x: CITIES[TEAM_CITIES[x]]["state"])

    return data_frame.assign(out_of_state=(team_state != venue_state).astype(int))


# Got the formula from https://www.movable-type.co.uk/scripts/latlong.html


def _haversine_formula(
    lat_long1: Tuple[float, float], lat_long2: Tuple[float, float]
) -> float:
    """Formula for distance between two pairs of latitudes & longitudes"""

    lat1, long1 = lat_long1
    lat2, long2 = lat_long2
    # Latitude & longitude are in degrees, so have to convert to radians for
    # trigonometric functions
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = math.radians(long2 - long1)
    a = math.sin(delta_phi / 2) ** 2 + (
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS * c


def add_travel_distance(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Add distance between each team's home city and the venue city for the match"""

    if any([req_col not in data_frame.columns for req_col in ["venue", "team"]]):
        raise ValueError(
            "To calculate travel distance, 'venue' and 'team' "
            "must be in the data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    venue_lat_long = data_frame["venue"].map(
        lambda x: (CITIES[VENUE_CITIES[x]]["lat"], CITIES[VENUE_CITIES[x]]["long"])
    )
    team_lat_long = data_frame["team"].map(
        lambda x: (CITIES[TEAM_CITIES[x]]["lat"], CITIES[TEAM_CITIES[x]]["long"])
    )

    return data_frame.assign(
        travel_distance=[
            _haversine_formula(*lats_longs)
            for lats_longs in zip(venue_lat_long, team_lat_long)
        ]
    )


def add_last_year_brownlow_votes(data_frame: pd.DataFrame):
    """Add column for a player's total brownlow votes from the previous season"""

    REQUIRED_COLS = ["player_id", "year", "brownlow_votes"]

    if any([req_col not in data_frame.columns for req_col in REQUIRED_COLS]):
        raise ValueError(
            f"To calculate yearly brownlow votes, the columns {REQUIRED_COLS} "
            "must be in the data frame, but the columns given were "
            f"{data_frame.columns}"
        )

    brownlow_last_year = (
        data_frame[["player_id", "year", "brownlow_votes"]]
        .groupby(["player_id", "year"], group_keys=True)
        .sum()
        # Grouping by player to shift by year
        .groupby(level=0)
        .shift()
        .fillna(0)
        .rename(columns={"brownlow_votes": "last_year_brownlow_votes"})
    )
    return (
        data_frame.drop("brownlow_votes", axis=1)
        .merge(brownlow_last_year, on=["player_id", "year"], how="left")
        .set_index(data_frame.index)
    )


def add_rolling_player_stats(data_frame: pd.DataFrame):
    """Replace players' invidual match stats with rolling averages of those stats"""

    STATS_COLS = [
        "player_id",
        "kicks",
        "marks",
        "handballs",
        "goals",
        "behinds",
        "hit_outs",
        "tackles",
        "rebounds",
        "inside_50s",
        "clearances",
        "clangers",
        "frees_for",
        "frees_against",
        "contested_possessions",
        "uncontested_possessions",
        "contested_marks",
        "marks_inside_50",
        "one_percenters",
        "bounces",
        "goal_assists",
        "time_on_ground",
    ]

    rolling_stats_cols = {
        stats_col: f"rolling_prev_match_{stats_col}"
        for stats_col in STATS_COLS
        if stats_col != "player_id"
    }

    if any([req_col not in data_frame.columns for req_col in STATS_COLS]):
        raise ValueError(
            "To calculate rolling player stats, the stats columns "
            f"{STATS_COLS} must be in the data frame, but the columns"
            f"given were {list(data_frame.columns)}"
        )

    player_data_frame = data_frame.sort_values(["player_id", "year", "round_number"])
    player_groups = (
        player_data_frame[STATS_COLS]
        .groupby("player_id", group_keys=False)
        .shift()
        .assign(player_id=player_data_frame["player_id"])
        .fillna(0)
        .groupby("player_id", group_keys=False)
    )

    rolling_stats = player_groups.rolling(window=23).mean()
    expanding_stats = player_groups.expanding(1).mean()
    player_stats = (
        rolling_stats.fillna(expanding_stats).drop("player_id", axis=1).sort_index()
    )

    return player_data_frame.assign(**player_stats.to_dict("series")).rename(
        columns=rolling_stats_cols
    )


def add_cum_matches_played(data_frame: pd.DataFrame):
    """Add cumulative number of matches each player has played"""

    if "player_id" not in data_frame.columns:
        raise ValueError(
            "To calculate cum_matches_played, 'player_id' must be "
            "in the data frame, but the columns given were "
            f"{list(data_frame.columns)}"
        )

    return data_frame.assign(
        cum_matches_played=data_frame.groupby("player_id").cumcount()
    )


# Basing ELO calculations on:
# http://www.matterofstats.com/mafl-stats-journal/2013/10/13/building-your-own-team-rating-system.html
def _elo_formula(
    prev_elo_rating: float, prev_oppo_elo_rating: float, margin: int, at_home: bool
):
    hga = HGA if at_home else HGA * -1
    expected_outcome = 1 / (
        1 + 10 ** ((prev_oppo_elo_rating - prev_elo_rating - hga) / S)
    )
    actual_outcome = X + 0.5 - X ** (1 + (margin / M))

    return prev_elo_rating + (K * (actual_outcome - expected_outcome))


def _calculate_elo_rating(prev_match: pd.Series, cum_elo_ratings: pd.Series, year: int):
    if cum_elo_ratings is None or prev_match is None:
        return BASE_RATING
    else:
        prev_year, prev_round, _ = prev_match.name

        prev_elo_rating = cum_elo_ratings.loc[prev_match.name]

        if isinstance(prev_elo_rating, pd.Series):
            raise TypeError(
                f"ELO series returned a subsection of itself at index {prev_match.name} "
                "when a single value is expected. Check the data frame for duplicate "
                "index values."
            )

        prev_oppo_elo_rating = cum_elo_ratings.loc[
            prev_year, prev_round, prev_match["oppo_team"]
        ]
        prev_margin = prev_match["score"] - prev_match["oppo_score"]
        prev_at_home = bool(prev_match["at_home"])

        elo_rating = _elo_formula(
            prev_elo_rating, prev_oppo_elo_rating, prev_margin, prev_at_home
        )

    if prev_match["year"] != year:
        return (elo_rating * CARRYOVER) + (BASE_RATING * (1 - CARRYOVER))

    return elo_rating


def _get_previous_match(
    data_frame: pd.DataFrame, year: int, round_number: int, team: str
):
    prev_team_matches = data_frame.loc[
        (data_frame["team"] == team)
        & (data_frame["year"] == year)
        & (data_frame["round_number"] < round_number),
        :,
    ]

    # If we can't find any previous matches this season, filter by last season
    if not prev_team_matches.any().any():
        prev_team_matches = data_frame.loc[
            (data_frame["team"] == team) & (data_frame["year"] == year - 1), :
        ]

    if not prev_team_matches.any().any():
        return None

    return prev_team_matches.iloc[-1, :]


# Assumes df sorted by year & round_number, with ascending=True in order to find teams'
# previous matches
def _calculate_match_elo_rating(
    root_data_frame: pd.DataFrame,
    cum_elo_ratings: Optional[pd.Series],
    items: Tuple[EloIndexType, pd.Series],
):
    data_frame = root_data_frame.copy()
    index, _ = items
    year, round_number, team = index

    prev_match = _get_previous_match(data_frame, year, round_number, team)
    elo_rating = _calculate_elo_rating(prev_match, cum_elo_ratings, year)

    elo_data = [elo_rating]
    elo_index = pd.MultiIndex.from_tuples([(year, round_number, team)])
    elo_ratings = pd.Series(data=elo_data, index=elo_index)

    if cum_elo_ratings is None:
        return elo_ratings.copy()

    return cum_elo_ratings.append(elo_ratings)


def add_elo_rating(data_frame: pd.DataFrame):
    """Add ELO rating of team prior to matches"""

    if "score" not in data_frame.columns or "oppo_score" not in data_frame.columns:
        raise ValueError(
            "To calculate ELO ratings, 'score' and 'oppo_score' must be "
            "in the data frame, but the columns given were "
            f"{list(data_frame.columns)}"
        )

    elo_data_frame = data_frame.reorder_levels(
        [YEAR_LEVEL, ROUND_LEVEL, TEAM_LEVEL]
    ).sort_index(ascending=True)

    elo_column = (
        reduce(
            partial(_calculate_match_elo_rating, elo_data_frame),
            elo_data_frame.iterrows(),
            None,
        )
        .reorder_levels(
            [REORDERED_TEAM_LEVEL, REORDERED_YEAR_LEVEL, REORDERED_ROUND_LEVEL]
        )
        .sort_index()
    )

    return data_frame.assign(elo_rating=elo_column)


def _shift_features(columns: List[str], shift: bool, data_frame: pd.DataFrame):
    columns_to_shift = (
        columns if shift else list(data_frame.drop(columns, axis=1).columns)
    )
    shifted_col_names = {col: f"prev_match_{col}" for col in columns_to_shift}

    # Group by team (not team & year) to get final score from previous season for round 1.
    # This reduces number of rows that need to be dropped and prevents gaps
    # for cumulative features
    shifted_features = (
        data_frame.groupby("team")[columns_to_shift]
        .shift()
        .fillna(0)
        .rename(columns=shifted_col_names)
    )

    return pd.concat([data_frame, shifted_features], axis=1)


def add_shifted_team_features(
    shift_columns: List[str] = [], keep_columns: List[str] = []
):
    """
    Group features by team and shift by one to get previous match stats.
    Use shift_columns to indicate which features to shift or keep_columns for features
    to leave unshifted, but not both.
    """

    if any(shift_columns) and any(keep_columns):
        raise ValueError(
            "To avoid conflicts, you can't include both match_cols "
            "and oppo_feature_cols. Choose the shorter list to determine which "
            "columns to skip and which to turn into opposition features."
        )

    shift = any(shift_columns)
    columns = shift_columns if shift else keep_columns

    return partial(_shift_features, columns, shift)
