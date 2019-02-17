from functools import reduce, partial
import pandas as pd
import numpy as np

WIN_POINTS = 4
# Constants for ELO calculations
BASE_RATING = 1000
K = 35.6
X = 0.49
M = 130
# Home Ground Advantage
HGA = 9
S = 250
CARRYOVER = 0.575
INDEX_COLS = ["team", "year", "round_number"]
TEAM_CITIES = {
    "Adelaide": "Adelaide",
    "Brisbane": "Brisbane",
    "Carlton": "Melbourne",
    "Collingwood": "Melbourne",
    "Essendon": "Melbourne",
    "Fitzroy": "Melbourne",
    "Western Bulldogs": "Melbourne",
    "Fremantle": "Perth",
    "GWS": "Sydney",
    "Geelong": "Geelong",
    "Gold Coast": "Gold Coast",
    "Hawthorn": "Melbourne",
    "Melbourne": "Melbourne",
    "North Melbourne": "Melbourne",
    "Port Adelaide": "Adelaide",
    "Richmond": "Melbourne",
    "St Kilda": "Melbourne",
    "Sydney": "Sydney",
    "University": "Melbourne",
    "West Coast": "Perth",
}

CITIES = {
    "Adelaide": {"state": "SA", "lat": -34.9285, "long": 138.6007},
    "Sydney": {"state": "NSW", "lat": -33.8688, "long": 151.2093},
    "Melbourne": {"state": "VIC", "lat": -37.8136, "long": 144.9631},
    "Geelong": {"state": "VIC", "lat": -38.1499, "long": 144.3617},
    "Perth": {"state": "WA", "lat": -31.9505, "long": 115.8605},
    "Gold Coast": {"state": "QLD", "lat": -28.0167, "long": 153.4000},
    "Brisbane": {"state": "QLD", "lat": -27.4698, "long": 153.0251},
    "Launceston": {"state": "TAS", "lat": -41.4332, "long": 147.1441},
    "Canberra": {"state": "ACT", "lat": -35.2809, "long": 149.1300},
    "Hobart": {"state": "TAS", "lat": -42.8821, "long": 147.3272},
    "Darwin": {"state": "NT", "lat": -12.4634, "long": 130.8456},
    "Alice Springs": {"state": "NT", "lat": -23.6980, "long": 133.8807},
    "Wellington": {"state": "NZ", "lat": -41.2865, "long": 174.7762},
    "Euroa": {"state": "VIC", "lat": -36.7500, "long": 145.5667},
    "Yallourn": {"state": "VIC", "lat": -38.1803, "long": 146.3183},
    "Cairns": {"state": "QLD", "lat": -6.9186, "long": 145.7781},
    "Ballarat": {"state": "VIC", "lat": -37.5622, "long": 143.8503},
    "Shanghai": {"state": "CHN", "lat": 31.2304, "long": 121.4737},
    "Albury": {"state": "NSW", "lat": -36.0737, "long": 146.9135},
}


def city_lat_long(city):
    return CITIES[city]["lat"], CITIES[city]["long"]


def team_match_id(df):
    return (
        df["year"].astype(str) + "." + df["round_number"].astype(str) + "." + df["team"]
    )


def match_result(margin):
    if margin > 0:
        return 1
    if margin < 0:
        return 0
    return 0.5


def home_away_df(at_home, df):
    team_label = "home_" if at_home else "away_"
    margin = df["home_margin"] if at_home else df["home_margin"] * -1

    return (
        df.filter(regex=f"^{team_label}|year|round_number|match_id|date")
        .drop_duplicates()
        .rename(columns=lambda col: col.replace(team_label, ""))
        .assign(
            at_home=at_home,
            team_match_id=team_match_id,
            margin=margin,
            oppo_score=lambda df: df["score"] - margin,
            match_result=margin.map(match_result),
        )
        .assign(match_points=lambda df: df["match_result"] * WIN_POINTS)
        .set_index(INDEX_COLS, drop=False)
        .rename_axis([None, None, None])
    )


# Calculates the ladder position at the end of the round of the given match
def ladder_position(data_frame):
    df = data_frame.sort_index()

    cum_match_points = df.groupby(["team", "year"])["match_points"].cumsum()

    cum_score = df.groupby(["team", "year"])["score"].cumsum()

    cum_oppo_score = df.groupby(["team", "year"])["oppo_score"].cumsum()

    # Pivot to get round-by-round match points and cumulative percent
    ladder_pivot_table = (
        df.assign(
            cum_match_points=cum_match_points, cum_percent=(cum_score / cum_oppo_score)
        )
        .loc[:, INDEX_COLS + ["cum_match_points", "cum_percent"]]
        .pivot_table(
            index=["year", "round_number"],
            values=["cum_match_points", "cum_percent"],
            columns="team",
            aggfunc={"cum_match_points": np.sum, "cum_percent": np.mean},
        )
    )

    # To get round-by-round ladder ranks, we sort each round by win points & percent,
    # then save index numbers
    ladder_index = []
    ladder_values = []

    for year_round_idx, round_row in ladder_pivot_table.iterrows():
        sorted_row = round_row.unstack(level=0).sort_values(
            ["cum_match_points", "cum_percent"], ascending=False
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

    return ladder_position_col


# Basing ELO calculations on:
# http://www.matterofstats.com/mafl-stats-journal/2013/10/13/building-your-own-team-rating-system.html
def _elo_formula(prev_elo_rating, prev_oppo_elo_rating, margin, at_home):
    hga = HGA if at_home else HGA * -1
    expected_outcome = 1 / (
        1 + 10 ** ((prev_oppo_elo_rating - prev_elo_rating - hga) / S)
    )
    actual_outcome = X + 0.5 - X ** (1 + (margin / M))

    return prev_elo_rating + (K * (actual_outcome - expected_outcome))


def _cross_year_elo(elo_rating):
    return (elo_rating * CARRYOVER) + (BASE_RATING * (1 - CARRYOVER))


def _calculate_prev_elo_ratings(prev_match, prev_oppo_match, cum_elo_ratings, year):
    if cum_elo_ratings is None:
        return BASE_RATING, BASE_RATING

    if prev_match is None:
        prev_elo_rating = BASE_RATING
    else:
        prev_elo_rating = cum_elo_ratings.loc[prev_match.name]

        if prev_match["year"] != year:
            prev_elo_rating = _cross_year_elo(prev_elo_rating)

    if prev_oppo_match is None:
        prev_oppo_elo_rating = BASE_RATING
    else:
        prev_oppo_elo_rating = cum_elo_ratings.loc[prev_oppo_match.name]

        if prev_oppo_match["year"] != year:
            prev_oppo_elo_rating = _cross_year_elo(prev_oppo_elo_rating)

    if isinstance(prev_elo_rating, pd.Series):
        raise TypeError(
            f"ELO series returned a subsection of itself at index {prev_match.name} "
            "when a single value is expected. Check the data frame for duplicate "
            "index values."
        )

    if isinstance(prev_oppo_elo_rating, pd.Series):
        raise TypeError(
            f"ELO series returned a subsection of itself at index {prev_oppo_match.name} "
            "when a single value is expected. Check the data frame for duplicate "
            "index values."
        )

    return prev_elo_rating, prev_oppo_elo_rating


def _calculate_elo_rating(prev_match, prev_oppo_match, match_row, cum_elo_ratings):
    prev_elo_rating, prev_oppo_elo_rating = _calculate_prev_elo_ratings(
        prev_match, prev_oppo_match, cum_elo_ratings, match_row["year"]
    )

    margin = match_row["margin"]
    at_home = bool(match_row["at_home"])

    return _elo_formula(prev_elo_rating, prev_oppo_elo_rating, margin, at_home)


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
def _calculate_match_elo_rating(root_data_frame, cum_elo_ratings, items):
    data_frame = root_data_frame.copy()
    index, match_row = items
    year, round_number, team = index
    oppo_team = data_frame.loc[
        (data_frame["match_id"] == match_row["match_id"])
        & (data_frame["team"] != team),
        "team",
    ].iloc[0]

    prev_match = _get_previous_match(data_frame, year, round_number, team)
    prev_oppo_match = _get_previous_match(data_frame, year, round_number, oppo_team)
    elo_rating = _calculate_elo_rating(
        prev_match, prev_oppo_match, match_row, cum_elo_ratings
    )

    elo_data = [elo_rating]
    elo_index = pd.MultiIndex.from_tuples([(year, round_number, team)])
    elo_ratings = pd.Series(data=elo_data, index=elo_index)

    if cum_elo_ratings is None:
        return elo_ratings.copy()

    return cum_elo_ratings.append(elo_ratings)


def add_elo_rating(data_frame):
    elo_data_frame = data_frame.reorder_levels([1, 2, 0]).sort_index(ascending=True)

    elo_column = (
        reduce(
            partial(_calculate_match_elo_rating, elo_data_frame),
            elo_data_frame.iterrows(),
            None,
        )
        .reorder_levels([2, 0, 1])
        .sort_index()
    )

    return elo_column


def match_id(data_frame):
    teams = data_frame["home_team"].str.cat(data_frame["away_team"], sep=".")
    # Need to sort teams alphabetically, because some edge cases with draws & repeated matches
    # make consistent IDs difficult if based on home/away team names
    sorted_teams = teams.map(lambda teams: ".".join(sorted(teams.split("."))))

    return (
        data_frame["year"].astype(str)
        + "."
        + data_frame["round_number"].astype(str)
        + "."
        + sorted_teams
    )


def player_team_match_id(df):
    return df["team_match_id"] + "." + df["player_id"].astype(str)


def playing_for_team_match_id(df):
    return (
        df["year"].astype(str)
        + "."
        + df["round_number"].astype(str)
        + "."
        + df["playing_for"]
    )
