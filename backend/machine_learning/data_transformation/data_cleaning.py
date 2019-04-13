"""Module for data cleaning functions"""

from typing import Optional, Pattern
from datetime import datetime, date
import re
import pandas as pd

from machine_learning.data_config import TEAM_TRANSLATIONS, FOOTYWIRE_VENUE_TRANSLATIONS
from project.settings.common import MELBOURNE_TIMEZONE

MATCH_COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
PLAYER_COL_TRANSLATIONS = {
    "time_on_ground__": "time_on_ground",
    "id": "player_id",
    "game": "match_id",
}
REGULAR_ROUND: Pattern = re.compile(r"round\s+(\d+)$", flags=re.I)

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


def _map_betting_teams_to_match_teams(team_name: str) -> str:
    if team_name in TEAM_TRANSLATIONS.keys():
        return TEAM_TRANSLATIONS[team_name]

    return team_name


def _concatenate_betting_and_match_data(
    betting_data: pd.DataFrame, match_data: pd.DataFrame
) -> pd.DataFrame:
    betting_data = betting_data.drop(
        [
            "date",
            "venue",
            "round_label",
            "home_score",
            "home_margin",
            "away_score",
            "away_margin",
        ],
        axis=1,
    ).assign(
        home_team=lambda df: df["home_team"].map(_map_betting_teams_to_match_teams),
        away_team=lambda df: df["away_team"].map(_map_betting_teams_to_match_teams),
    )
    match_data = match_data.drop(["date", "venue", "round_label"], axis=1)

    return betting_data.merge(
        match_data, on=["home_team", "away_team", "round", "season"]
    )


def clean_betting_data(
    betting_data: pd.DataFrame, match_data: pd.DataFrame
) -> pd.DataFrame:
    return (
        _concatenate_betting_and_match_data(betting_data, match_data)
        .rename(columns={"season": "year", "round": "round_number"})
        .drop(
            [
                "crowd",
                "home_win_paid",
                "home_line_paid",
                "away_win_paid",
                "away_line_paid",
            ],
            axis=1,
        )
    )


def _map_footywire_venues(venue: str) -> str:
    if venue not in FOOTYWIRE_VENUE_TRANSLATIONS.keys():
        return venue

    return FOOTYWIRE_VENUE_TRANSLATIONS[venue]


def _round_type_column(data_frame: pd.DataFrame) -> pd.DataFrame:
    return data_frame["round_label"].map(
        lambda label: "Finals" if re.search(REGULAR_ROUND, label) is None else "Regular"
    )


def _match_data_from_next_round(future_match_data):
    right_now = datetime.now(tz=MELBOURNE_TIMEZONE)  # pylint: disable=W0612
    next_round = future_match_data.query("date > @right_now")["round"].min()

    return (
        future_match_data.assign(round_type=_round_type_column)
        .loc[
            future_match_data["round"] == next_round,
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
        .assign(venue=lambda df: df["venue"].map(_map_footywire_venues))
    )


def clean_match_data(
    past_match_data: pd.DataFrame, future_match_data: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    match_data = (
        past_match_data.rename(columns=MATCH_COL_TRANSLATIONS)
        # fitzRoy returns integers that represent some sort of datetime, and the only
        # way to parse them is converting them to dates.
        # NOTE: If the matches parsed only go back to 1990 (give or take, I can't remember)
        # you can parse the date integers into datetime
        .assign(date=lambda df: pd.to_datetime(df["date"], unit="D"))
        .astype({"year": int})
        .drop(["round", "game"], axis=1)
        # There were some weird round-robin rounds in the early days, and it's easier to
        # drop them rather than figure out how to split up the rounds.
        .query(
            "((year != 1897) | (round_number != 15)) & "
            "((year != 1924) | (round_number != 19))"
        )
    )

    if future_match_data is None:
        return match_data

    return (
        pd.concat(
            [match_data, _match_data_from_next_round(future_match_data)], sort=False
        )
        .reset_index(drop=True)
        .drop_duplicates(
            subset=["date", "venue", "year", "round_number", "home_team", "away_team"]
        )
        .fillna(0)
    )


def _player_id_col(data_frame: pd.DataFrame) -> pd.DataFrame:
    return (
        data_frame["player_id"].astype(str)
        + data_frame["match_id"].astype(str)
        + data_frame["year"].astype(str)
    )


def _clean_roster_data(
    roster_data: pd.DataFrame, player_data_frame: pd.DataFrame
) -> pd.DataFrame:
    if not roster_data.any().any():
        return roster_data.assign(player_id=[])

    year = date.today().year

    roster_data_frame = (
        roster_data.merge(
            player_data_frame[["player_name", "player_id"]],
            on=["player_name"],
            how="left",
        )
        .sort_values("player_id", ascending=False)
        # There are some duplicate player names over the years, so we drop the oldest,
        # hoping that the contemporary player matches the one with the most-recent
        # entry into the AFL. If two players with the same name are playing in the
        # league at the same time, that will likely result in errors
        .drop_duplicates(subset=["player_name"], keep="first")
        .assign(year=year)
    )
    # If a player is new to the league, he won't have a player_id per AFL Tables data,
    # so we make one up just using his name
    roster_data_frame["player_id"].fillna(
        roster_data_frame["player_name"], inplace=True
    )

    return roster_data_frame.assign(id=_player_id_col).set_index("id")


def clean_player_data(
    player_data: pd.DataFrame,
    match_data: pd.DataFrame,
    roster_data: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    data_frame = (
        player_data
        # Some player data venues have trailing spaces
        .assign(venue=lambda x: x["venue"].str.strip())
        # Player data match IDs are wrong for recent years.
        # The easiest way to add correct ones is to graft on the IDs
        # from match_results. Also, match_results round_numbers are more useful.
        .merge(
            match_data[["date", "venue", "round_number", "game"]],
            on=["date", "venue"],
            how="left",
        )
        # As of 11-10-2018, match_results is still missing finals data from 2018.
        # Joining on date/venue leaves two duplicates played at M.C.G.
        # on 29-4-1986 & 9-8-1986, but that's an acceptable loss of data
        # and easier than munging team names
        .dropna()
        .rename(columns={**MATCH_COL_TRANSLATIONS, **PLAYER_COL_TRANSLATIONS})
        .astype({"year": int, "match_id": str, "player_id": str})
        .assign(
            player_name=lambda x: x["first_name"] + " " + x["surname"],
            # Need to add year to ID, because there are some
            # player_id/match_id combos, decades apart, that by chance overlap
            id=_player_id_col,
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
    duplicate_match_ids = data_frame[
        data_frame.duplicated(subset=["year", "round_number", "player_id"], keep="last")
    ]["match_id"]

    # There were some weird round-robin rounds in the early days, and it's easier to
    # drop them rather than figure out how to split up the rounds.
    data_frame = data_frame[
        ((data_frame["year"] != 1897) | (data_frame["round_number"] != 15))
        & ((data_frame["year"] != 1924) | (data_frame["round_number"] != 19))
        & (~data_frame["match_id"].isin(duplicate_match_ids))
    ]

    if roster_data is None:
        return data_frame

    roster_data_frame = _clean_roster_data(roster_data, data_frame)

    return pd.concat([data_frame, roster_data_frame], sort=False).fillna(0)
