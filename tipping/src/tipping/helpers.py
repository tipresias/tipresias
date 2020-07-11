"""Helper functions."""

from typing import Dict, Callable, List, Any
import pandas as pd
import numpy as np


NON_METRIC_COLS = ["home_team", "away_team", "year", "round_number", "ml_model"]


def _replace_metric_col_names(team_type: str) -> Callable:
    return lambda col: col if col in NON_METRIC_COLS else team_type + "_" + col


def _replace_team_col_names(team_type: str) -> Dict[str, str]:
    oppo_team_type = "away" if team_type == "home" else "home"

    return {"team": team_type + "_team", "oppo_team": oppo_team_type + "_team"}


def _home_away_data_frame(data_frame: pd.DataFrame, team_type: str) -> pd.DataFrame:
    is_at_home = team_type == "home"
    at_home_query = 1 if is_at_home else 0  # pylint: disable=W0612

    return (
        data_frame.query("at_home == @at_home_query")
        .drop("at_home", axis=1)
        .rename(columns=_replace_team_col_names(team_type))
        .rename(columns=_replace_metric_col_names(team_type))
        .reset_index(drop=True)
    )


def pivot_team_matches_to_matches(team_match_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots data frame from team-match rows to match rows with home_ and away_ columns.

    Due to how columns are renamed, currently only works for prediction data frames.

    Params:
    -------
    team_match_df: Prediction data structured to have two rows per match
        (one for each participating team) with team & oppo_team columns

    Returns:
    --------
    Prediction data frame reshaped to have one row per match, with columns for home_team
        and away_team.
    """
    home_data_frame = _home_away_data_frame(team_match_df, "home")
    away_data_frame = _home_away_data_frame(team_match_df, "away")

    return home_data_frame.merge(
        away_data_frame,
        on=["home_team", "away_team", "year", "round_number", "ml_model"],
        how="inner",
    )


def convert_to_dict(data_frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to list of record dicts with necessary dtype conversions.

    Params:
    -------
    data_frame: Any old data frame you choose.

    Returns:
    --------
    List of dicts.
    """
    type_conversion = {"date": str} if "date" in data_frame.columns else {}
    return data_frame.replace({np.nan: None}).astype(type_conversion).to_dict("records")
