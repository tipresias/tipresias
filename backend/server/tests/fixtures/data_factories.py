"""Module for factory functions that create raw data objects."""

from typing import List, Dict, Tuple, Union, cast, Any
from datetime import datetime, timedelta
import itertools
import pytz
from dateutil import parser

from faker import Faker
import numpy as np
import pandas as pd
from django.utils import timezone
from django.conf import settings
import candystore
from mypy_extensions import TypedDict

from server.types import FixtureData, MatchData
from server.models import Match


RawFixtureData = TypedDict(
    "RawFixtureData",
    {
        "date": str,
        "season": int,
        "season_game": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)


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
        """
        Instantiate a CyclicalTeamNames object.

        Params:
        -------
        team_names: List of team names to cycle through. Defaults to all teams
            currently in the AFL.
        """
        self.team_names = team_names
        self.cyclical_team_names = (name for name in self.team_names)

    def next_team(self) -> str:
        """Return the next team name or start over from the beginning."""
        try:
            return next(self.cyclical_team_names)
        except StopIteration:
            self.cyclical_team_names = (name for name in self.team_names)

            return next(self.cyclical_team_names)


def _min_max_datetimes_by_year(
    year: int, force_future: bool = False
) -> Dict[str, datetime]:
    # About as early as matches ever start
    MIN_MATCH_HOUR = 12
    # About as late as matches ever start
    MAX_MATCH_HOUR = 20

    if force_future:
        today = timezone.now()

        # Running tests on 28 Feb of a leap year breaks them, because the given year
        # generally won't be a leap year (e.g. 2018-2-29 doesn't exist),
        # so we retry with two days in the future (e.g. 2018-3-1).
        try:
            tomorrow = today + timedelta(hours=24)
            datetime_start = timezone.make_aware(
                datetime(year, tomorrow.month, tomorrow.day, MIN_MATCH_HOUR)
            )
        except ValueError:
            tomorrow = today + timedelta(hours=48)
            datetime_start = timezone.make_aware(
                datetime(year, tomorrow.month, tomorrow.day, MIN_MATCH_HOUR)
            )
    else:
        datetime_start = timezone.make_aware(datetime(year, JAN, FIRST, MIN_MATCH_HOUR))

    return {
        "datetime_start": datetime_start,
        "datetime_end": timezone.make_aware(
            datetime(year, DEC, THIRTY_FIRST, MAX_MATCH_HOUR)
        ),
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
        _raw_match_data(year, (team_names.next_team(), team_names.next_team()))
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


def _clean_fixture(fixture: RawFixtureData) -> FixtureData:
    clean_fixture: Dict[str, Any] = {
        **cast(Dict[str, Any], fixture),
        "year": fixture["season"],
        "round_number": fixture["round"],
    }

    del clean_fixture["season_game"]

    # Recreates data cleaning performed in views.fixtures
    clean_fixture["date"] = parser.parse(fixture["date"]).replace(tzinfo=pytz.UTC)

    return cast(FixtureData, clean_fixture)


def fake_fixture_data(year_range: Tuple[int, int]) -> List[FixtureData]:
    """
    Return minimally-valid data for fixture data.

    These matches are usually unplayed, future matches, but it is also possible to get
    data for past fixtures.
    """
    return [
        _clean_fixture(fixture) for fixture in candystore.generate_fixtures(year_range)
    ]


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
