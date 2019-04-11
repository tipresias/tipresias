"""Module for data cleaning functions"""

from typing import Optional, Pattern
from datetime import datetime
import re
import pandas as pd

from machine_learning.data_config import TEAM_TRANSLATIONS, FOOTYWIRE_VENUE_TRANSLATIONS
from project.settings.common import MELBOURNE_TIMEZONE

COL_TRANSLATIONS = {
    "home_points": "home_score",
    "away_points": "away_score",
    "margin": "home_margin",
    "season": "year",
}
REGULAR_ROUND: Pattern = re.compile(r"round\s+(\d+)$", flags=re.I)


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
        past_match_data.rename(columns=COL_TRANSLATIONS)
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
