"""Helper functions"""

from typing import Dict
import pandas as pd


def _replace_col_names(team_type: str) -> Dict[str, str]:
    oppo_team_type = "away" if team_type == "home" else "home"

    return {
        "team": team_type + "_team",
        "oppo_team": oppo_team_type + "_team",
        "predicted_margin": team_type + "_predicted_margin",
    }


def _home_away_data_frame(data_frame: pd.DataFrame, team_type: str) -> pd.DataFrame:
    is_at_home = team_type == "home"
    at_home_query = 1 if is_at_home else 0  # pylint: disable=W0612

    return (
        data_frame.query("at_home == @at_home_query")
        .drop("at_home", axis=1)
        .rename(columns=_replace_col_names(team_type))
        .reset_index()
    )


def pivot_team_matches_to_matches(team_match_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots per at_home column to change team-match rows with team and oppo_ columns
    to match rows with home_ and away_ columns. Due to how columns are renamed,
    currently only works for prediction data frames.

    Args:
        team_match_df (pd.DataFrame): DataFrame structured to have two rows per match
            (one for each participating team) with team & oppo_team columns

    Returns:
        pd.DataFrame: Reshaped to have one row per match, with columns for home_team
            and away_team.
    """

    home_data_frame = _home_away_data_frame(team_match_df, "home")
    away_data_frame = _home_away_data_frame(team_match_df, "away")

    return home_data_frame.merge(
        away_data_frame,
        on=["home_team", "away_team", "year", "round_number", "ml_model"],
        how="inner",
    )
