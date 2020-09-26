"""Module for factory functions that create raw data objects."""

from typing import List, Dict, Tuple, Union
from datetime import datetime, timedelta, date
import itertools
import pytz

from faker import Faker
import numpy as np
import pandas as pd
from mypy_extensions import TypedDict
from candystore import CandyStore

from tipping import settings
from tipping.types import FixtureData, MatchData


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
        today = datetime.now(tz=pytz.UTC)

        # Running tests on 28 Feb of a leap year breaks them, because the given year
        # generally won't be a leap year (e.g. 2018-2-29 doesn't exist),
        # so we retry with two days in the future (e.g. 2018-3-1).
        try:
            tomorrow = today + timedelta(hours=24)
            datetime_start = datetime(
                year, tomorrow.month, tomorrow.day, MIN_MATCH_HOUR, tzinfo=pytz.UTC
            )
        except ValueError:
            tomorrow = today + timedelta(hours=48)
            datetime_start = datetime(
                year, tomorrow.month, tomorrow.day, MIN_MATCH_HOUR, tzinfo=pytz.UTC
            )
    else:
        datetime_start = datetime(year, JAN, FIRST, MIN_MATCH_HOUR, tzinfo=pytz.UTC)

    return {
        "datetime_start": datetime_start,
        "datetime_end": datetime(
            year, DEC, THIRTY_FIRST, MAX_MATCH_HOUR, tzinfo=pytz.UTC
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


def fake_match_data(year_range: Tuple[int, int]) -> pd.DataFrame:
    """Return minimally-valid dummy match results data."""
    return (
        CandyStore(seasons=year_range)
        .match_results(to_dict=None)
        .rename(
            columns={
                "season": "year",
                "home_points": "home_score",
                "away_points": "away_score",
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


def _results_by_match(round_number: int, team_names: CyclicalTeamNames):
    home_team = team_names.next_team()
    away_team = team_names.next_team()
    winner = np.random.choice([home_team, away_team])
    match_date = FAKE.date_time_between_dates(
        **_min_max_datetimes_by_year(date.today().year)
    )

    return {
        "date": str(match_date),
        "tz": "+10:00",
        "updated": str(match_date + timedelta(hours=3)),
        "round": round_number,
        "roundname": f"Round {round_number}",
        "year": date.today().year,
        "hbehinds": FAKE.pyint(1, 15),
        "hgoals": FAKE.pyint(1, 15),
        "hscore": FAKE.pyint(20, 120),
        "hteam": home_team,
        "hteamid": settings.TEAM_NAMES.index(home_team),
        "abehinds": FAKE.pyint(1, 15),
        "agoals": FAKE.pyint(1, 15),
        "ascore": FAKE.pyint(20, 120),
        "ateam": away_team,
        "ateamid": settings.TEAM_NAMES.index(away_team),
        "winner": winner,
        "winnerteamid": settings.TEAM_NAMES.index(winner),
        "is_grand_final": 0,
        "complete": 100,
        "is_final": 0,
        "id": FAKE.pyint(1, 200),
        "venue": np.random.choice(list(settings.VENUE_CITIES.keys())),
    }


def fake_match_results_data(row_count: int, round_number: int) -> pd.DataFrame:
    """
    Generate dummy data that replicates match results data.

    Params
    ------
    row_count: Number of match rows to return

    Returns
    -------
    DataFrame of match results data
    """
    team_names = CyclicalTeamNames()

    return pd.DataFrame(
        [_results_by_match(round_number, team_names) for _ in range(row_count)]
    )


def fake_prediction_data(
    match_data: Union[FixtureData, None] = None,
    ml_model_name="test_estimator",
    predict_margin=True,
) -> pd.DataFrame:
    """Return minimally-valid prediction data."""
    if match_data is None:
        match_data_for_pred = fake_fixture_data((2018, 2019))[0]
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


def fake_ml_model_data(n_models: int = 1) -> pd.DataFrame:
    """Generate mock data for raw ML model info from the Augury app."""
    return pd.DataFrame(
        [
            {
                "name": FAKE.company(),
                "prediction_type": np.random.choice(["margin", "win_probability"]),
                "trained_to": FAKE.pybool(),
                "data_set": np.random.choice(["legacy_model_data", "model_data"]),
                "label_col": np.random.choice(["margin", "result"]),
            }
            for _ in range(n_models)
        ]
    )
