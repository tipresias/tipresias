"""Module for factory functions that create raw data objects."""

from typing import Tuple, Union, Optional, Dict

from faker import Faker
import numpy as np
import pandas as pd
from django.utils import timezone
from candystore import CandyStore

from server.models import Match


FAKE = Faker()


def fake_match_results_data(
    match_results: Optional[pd.DataFrame] = None,
    seasons: Union[Tuple[int, int], int] = 1,
) -> pd.DataFrame:
    """Return minimally-valid dummy match results data."""
    match_results = (
        CandyStore(seasons=seasons).match_results(to_dict=None)
        if match_results is None
        else match_results
    )

    return match_results.assign(
        date=lambda df: pd.to_datetime(df["date"]).map(timezone.make_aware)
    ).rename(
        columns={
            "home_points": "home_score",
            "away_points": "away_score",
            "season": "year",
        }
    )


def fake_fixture_data(
    fixtures: Optional[pd.DataFrame] = None, seasons: Union[Tuple[int, int], int] = 1
) -> pd.DataFrame:
    """
    Return minimally-valid data for fixture data.

    These matches are usually unplayed, future matches, but it is also possible to get
    data for past fixtures.
    """
    fixtures = (
        CandyStore(seasons=seasons).fixtures(to_dict=None)
        if fixtures is None
        else fixtures
    )

    return (
        fixtures.rename(columns={"season": "year", "round": "round_number"}).drop(
            "season_game", axis=1, errors="ignore"
        )
        # Recreates data cleaning performed in views.fixtures
        .assign(date=lambda df: pd.to_datetime(df["date"], utc=True))
    )


def _fake_prediction_results(match_count, predict_margin) -> Dict[str, Optional[float]]:
    if predict_margin:
        return {
            "home_predicted_margin": np.random.uniform(25.0, 125.0, size=match_count),
            "away_predicted_margin": np.random.uniform(25.0, 125.0, size=match_count),
            "home_predicted_win_probability": None,
            "away_predicted_win_probability": None,
        }

    return {
        "home_predicted_margin": None,
        "away_predicted_margin": None,
        "home_predicted_win_probability": np.random.uniform(0.1, 0.9, size=match_count),
        "away_predicted_win_probability": np.random.uniform(0.1, 0.9, size=match_count),
    }


def _fake_match_data_for_pred(match_data):
    if isinstance(match_data, Match):
        return pd.DataFrame(
            [
                {
                    "date": match_data.start_date_time,
                    "home_team": match_data.teammatch_set.get(at_home=1).team.name,
                    "away_team": match_data.teammatch_set.get(at_home=0).team.name,
                    "year": match_data.start_date_time.year,
                    "round_number": match_data.round_number,
                    "venue": FAKE.city(),
                }
            ]
        )

    return fake_fixture_data(fixtures=match_data)


def fake_prediction_data(
    match_data: Optional[Union[pd.DataFrame, Match]] = None,
    ml_model_name="test_estimator",
    predict_margin=True,
) -> pd.DataFrame:
    """Return minimally-valid prediction data."""
    match_data_for_pred = _fake_match_data_for_pred(match_data)
    match_count = len(match_data_for_pred)

    return match_data_for_pred.loc[
        :, ["date", "home_team", "away_team", "year", "round_number"]
    ].assign(
        ml_model=ml_model_name, **_fake_prediction_results(match_count, predict_margin)
    )
