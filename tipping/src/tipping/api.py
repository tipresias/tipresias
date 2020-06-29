"""External-facing API for fetching and updating application data."""

from typing import Optional, List

import numpy as np

from tipping import data_import
from tipping.helpers import pivot_team_matches_to_matches
from tipping.types import CleanPredictionData, MatchData, MLModelInfo


def fetch_match_predictions(
    year_range: str,
    round_number: Optional[int] = None,
    ml_models: Optional[List[str]] = None,
    train_models: Optional[bool] = False,
) -> List[CleanPredictionData]:
    """
    Fetch prediction data from machine_learning module.

    Params:
    -------
    year_range: Min (inclusive) and max (exclusive) years for which to fetch data.
        Format is 'yyyy-yyyy'.
    round_number: Specify a particular round for which to fetch data.
    ml_models: List of ML model names to use for making predictions.
    train_models: Whether to train models in between predictions (only applies
        when predicting across multiple seasons).

    Returns:
    --------
        List of prediction data dictionaries.
    """

    prediction_data = data_import.fetch_prediction_data(
        year_range,
        round_number=round_number,
        ml_models=ml_models,
        train_models=train_models,
    )

    home_away_df = pivot_team_matches_to_matches(prediction_data)

    return home_away_df.replace({np.nan: None}).to_dict("records")


def fetch_match_results(
    start_date: str, end_date: str, fetch_data: bool = False
) -> List[MatchData]:
    """
    Fetch results data for past matches.

    Params:
    -------
    start_date: Date-time string that determines the earliest date
        for which to fetch data. Format is 'yyyy-mm-dd'.
    end_date: Date-time string that determines the latest date
        for which to fetch data. Format is 'yyyy-mm-dd'.
    fetch_data: Whether to fetch fresh data. Non-fresh data goes up to end
        of previous season.

    Returns:
    --------
        List of match results data dicts.
    """
    return data_import.fetch_match_results_data(
        start_date, end_date, fetch_data=fetch_data
    ).to_dict("records")


def fetch_ml_models() -> List[MLModelInfo]:
    """
    Fetch general info about all saved ML models.

    Returns:
    --------
    A list of objects with basic info about each ML model.
    """
    return data_import.fetch_ml_model_info().to_dict("records")
