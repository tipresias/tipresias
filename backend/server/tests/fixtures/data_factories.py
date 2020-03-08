"""Module for factory functions that create raw data objects."""

from typing import List, Dict, Tuple, Union
from datetime import datetime
import itertools
import pytz

from faker import Faker
import numpy as np
import pandas as pd
from django.utils import timezone
from django.conf import settings

from server.types import FixtureData, MatchData
from server.models import Match

FIRST = 1
SECOND = 2
JAN = 1
DEC = 12
THIRTY_FIRST = 31
FAKE = Faker()
CONTEMPORARY_TEAM_NAMES = [
    name for name in settings.TEAM_NAMES if name not in settings.DEFUNCT_TEAM_NAMES
]
BASELINE_BET_PAYOUT = 1.92


class CyclicalTeamNames:
    """Cycles through real team names per data config."""

    def __init__(self, team_names: List[str] = CONTEMPORARY_TEAM_NAMES):
        self.team_names = team_names
        self.cyclical_team_names = (name for name in self.team_names)

    def next(self) -> str:
        """Return the next team name or start over from the beginning."""
        try:
            return next(self.cyclical_team_names)
        except StopIteration:
            self.cyclical_team_names = (name for name in self.team_names)

            return next(self.cyclical_team_names)


def _min_max_datetimes_by_year(year: int) -> Dict[str, datetime]:
    return {
        "datetime_start": timezone.make_aware(datetime(year, JAN, FIRST)),
        "datetime_end": timezone.make_aware(datetime(year, DEC, THIRTY_FIRST)),
    }


def _raw_match_data(year: int, team_names: Tuple[str, str]) -> MatchData:
    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=pytz.UTC
        ),
        "year": year,
        "round": "R1",
        "round_number": 1,
        "home_team": team_names[0],
        "away_team": team_names[1],
        "venue": FAKE.city(),
        "home_score": np.random.randint(50, 150),
        "away_score": np.random.randint(50, 150),
        "match_id": FAKE.ean(),
        "crowd": np.random.randint(10000, 30000),
    }


def _matches_by_round(row_count: int, year: int) -> List[MatchData]:
    team_names = CyclicalTeamNames()

    return [
        _raw_match_data(year, (team_names.next(), team_names.next()))
        for _ in range(row_count)
    ]


def _matches_by_year(
    row_count: int, year_range: Tuple[int, int]
) -> List[List[MatchData]]:
    return [_matches_by_round(row_count, year) for year in range(*year_range)]


def fake_match_results_data(
    row_count: int, year_range: Tuple[int, int], clean=False
) -> pd.DataFrame:
    """Return minimally-valid dummy match results data."""
    data = _matches_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))
    data_frame = pd.DataFrame(list(reduced_data))

    if clean:
        return data_frame.rename(columns={"season": "year"})

    return data_frame


def _fixture_data(year: int, team_names: Tuple[str, str]) -> FixtureData:
    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=pytz.UTC
        ),
        "year": year,
        "round_number": 1,
        "home_team": team_names[0],
        "away_team": team_names[1],
        "venue": FAKE.city(),
    }


def _fixture_by_round(row_count: int, year: int) -> List[FixtureData]:
    team_names = CyclicalTeamNames()

    return [
        _fixture_data(year, (team_names.next(), team_names.next()))
        for idx in range(row_count)
    ]


def _fixture_by_year(
    row_count: int, year_range: Tuple[int, int]
) -> List[List[FixtureData]]:
    return [_fixture_by_round(row_count, year) for year in range(*year_range)]


def fake_fixture_data(row_count: int, year_range: Tuple[int, int]) -> pd.DataFrame:
    """
    Return minimally-valid data for fixture data.

    These matches are usually unplayed, future matches, but it is also possible to get
    data for past fixtures.
    """
    data = _fixture_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    return pd.DataFrame(list(reduced_data))


def fake_prediction_data(
    match_data: Union[FixtureData, Match, None] = None,
    ml_model_name="test_estimator",
    predict_margin=True,
) -> pd.DataFrame:
    """Return minimally-valid prediction data."""
    if match_data is None:
        match_data_for_pred = fake_fixture_data(1, (2018, 2019)).iloc[0, :]
    elif isinstance(match_data, Match):
        match_data_for_pred = {
            "home_team": match_data.teammatch_set.get(at_home=1).team.name,
            "away_team": match_data.teammatch_set.get(at_home=0).team.name,
            "year": match_data.start_date_time.year,
            "round_number": match_data.round_number,
        }
    else:
        match_data_for_pred = match_data

    predicted_home_margin = np.random.rand() * 50 if predict_margin else None
    predicted_away_margin = np.random.rand() * 50 if predict_margin else None
    predicted_home_proba = np.random.rand() if not predict_margin else None
    predicted_away_proba = np.random.rand() if not predict_margin else None

    predictions = [
        {
            "team": match_data_for_pred["home_team"],
            "year": match_data_for_pred["year"],
            "round_number": match_data_for_pred["round_number"],
            "at_home": 1,
            "oppo_team": match_data_for_pred["away_team"],
            "ml_model": ml_model_name,
            "predicted_margin": predicted_home_margin,
            "predicted_win_probability": predicted_home_proba,
        },
        {
            "team": match_data_for_pred["away_team"],
            "year": match_data_for_pred["year"],
            "round_number": match_data_for_pred["round_number"],
            "at_home": 0,
            "oppo_team": match_data_for_pred["home_team"],
            "ml_model": ml_model_name,
            "predicted_margin": predicted_away_margin,
            "predicted_win_probability": predicted_away_proba,
        },
    ]

    return pd.DataFrame(predictions)
