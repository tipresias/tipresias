"""Module for data cleaning functions"""

import pandas as pd

from machine_learning.data_config import TEAM_TRANSLATIONS


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
