"""Module for factory functions that create raw data objects."""

from typing import List, Tuple, Union

from faker import Faker
import numpy as np
import pandas as pd
from django.utils import timezone
from candystore import CandyStore

from server.types import FixtureData
from server.models import Match


FAKE = Faker()


def fake_match_results_data(year_range: Tuple[int, int]) -> pd.DataFrame:
    """Return minimally-valid dummy match results data."""
    return (
        CandyStore(seasons=year_range)
        .match_results(to_dict=None)
        .assign(date=lambda df: pd.to_datetime(df["date"]).map(timezone.make_aware))
        .rename(
            columns={
                "home_points": "home_score",
                "away_points": "away_score",
                "season": "year",
            }
        )
    )


def fake_fixture_data(year_range: Tuple[int, int]) -> List[FixtureData]:
    """
    Return minimally-valid data for fixture data.

    These matches are usually unplayed, future matches, but it is also possible to get
    data for past fixtures.
    """
    return (
        CandyStore(seasons=year_range)
        .fixtures(to_dict=None)
        .rename(columns={"season": "year", "round": "round_number"})
        .drop("season_game", axis=1)
        # Recreates data cleaning performed in views.fixtures
        .assign(date=lambda df: pd.to_datetime(df["date"], utc=True))
        .to_dict("records")
    )


def fake_prediction_data(
    match_data: Union[FixtureData, Match, None] = None,
    ml_model_name="test_estimator",
    predict_margin=True,
) -> pd.DataFrame:
    """Return minimally-valid prediction data."""
    if match_data is None:
        match_data_for_pred = fake_fixture_data((2018, 2019))[0]
    elif isinstance(match_data, Match):
        match_data_for_pred = {
            "date": match_data.start_date_time,
            "home_team": match_data.teammatch_set.get(at_home=1).team.name,
            "away_team": match_data.teammatch_set.get(at_home=0).team.name,
            "year": match_data.start_date_time.year,
            "round_number": match_data.round_number,
            "venue": FAKE.city(),
        }
    else:
        match_data_for_pred = match_data

    predicted_home_margin = np.random.uniform(25.0, 125.0) if predict_margin else None
    predicted_away_margin = np.random.uniform(25.0, 125.0) if predict_margin else None
    predicted_home_proba = np.random.uniform(0.1, 0.9) if not predict_margin else None
    predicted_away_proba = np.random.uniform(0.1, 0.9) if not predict_margin else None

    return pd.DataFrame(
        [
            {
                "date": match_data_for_pred["date"],
                "home_team": match_data_for_pred["home_team"],
                "away_team": match_data_for_pred["away_team"],
                "year": match_data_for_pred["year"],
                "round_number": match_data_for_pred["round_number"],
                "ml_model": ml_model_name,
                "home_predicted_margin": predicted_home_margin,
                "away_predicted_margin": predicted_away_margin,
                "home_predicted_win_probability": predicted_home_proba,
                "away_predicted_win_probability": predicted_away_proba,
            }
        ]
    )
