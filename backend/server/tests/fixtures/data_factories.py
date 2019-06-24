"""Module for factory functions that create raw data objects"""

from typing import List, Dict, Any, Tuple, Union
from datetime import datetime
import itertools

from faker import Faker
import numpy as np
import pandas as pd

from server.types import CleanFixtureData, MatchData
from server.models import Match
from project.settings.common import MELBOURNE_TIMEZONE
from project.settings.data import TEAM_NAMES, DEFUNCT_TEAM_NAMES

FIRST = 1
SECOND = 2
JAN = 1
DEC = 12
THIRTY_FIRST = 31
FAKE = Faker()
CONTEMPORARY_TEAM_NAMES = [
    name for name in TEAM_NAMES if name not in DEFUNCT_TEAM_NAMES
]
BASELINE_BET_PAYOUT = 1.92


class CyclicalTeamNames:
    def __init__(self, team_names: List[str] = CONTEMPORARY_TEAM_NAMES):
        self.team_names = team_names
        self.cyclical_team_names = (name for name in self.team_names)

    def next(self) -> str:
        try:
            return next(self.cyclical_team_names)
        except StopIteration:
            self.cyclical_team_names = (name for name in self.team_names)

            return next(self.cyclical_team_names)


def _min_max_datetimes_by_year(year: int) -> Dict[str, datetime]:
    return {
        "datetime_start": datetime(year, JAN, FIRST),
        "datetime_end": datetime(year, DEC, THIRTY_FIRST),
    }


def _raw_match_data(year: int, team_names: Tuple[str, str]) -> MatchData:
    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
        ),
        "season": year,
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
    data = _matches_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))
    data_frame = pd.DataFrame(list(reduced_data))

    if clean:
        return data_frame.rename(columns={"season": "year"})

    return data_frame


def _fixture_data(year: int, team_names: Tuple[str, str]) -> CleanFixtureData:
    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
        ),
        "year": year,
        "round_number": 1,
        "home_team": team_names[0],
        "away_team": team_names[1],
        "venue": FAKE.city(),
    }


def _fixture_by_round(row_count: int, year: int) -> List[CleanFixtureData]:
    team_names = CyclicalTeamNames()

    return [
        _fixture_data(year, (team_names.next(), team_names.next()))
        for idx in range(row_count)
    ]


def _fixture_by_year(
    row_count: int, year_range: Tuple[int, int]
) -> List[List[CleanFixtureData]]:
    return [_fixture_by_round(row_count, year) for year in range(*year_range)]


def fake_fixture_data(row_count: int, year_range: Tuple[int, int]) -> pd.DataFrame:
    data = _fixture_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    return pd.DataFrame(list(reduced_data))


def _betting_data(year: int, team_names: Tuple[str, str]) -> Dict[str, Any]:
    home_score, away_score = np.random.randint(50, 150), np.random.randint(50, 150)
    home_line_odds = np.random.randint(-50, 50)
    win_odds_diff = round((np.random.rand() * 0.8), 2)
    home_win_odds_diff = win_odds_diff if home_line_odds > 0 else -1 * win_odds_diff
    home_win_odds = BASELINE_BET_PAYOUT + home_win_odds_diff
    away_win_odds = BASELINE_BET_PAYOUT - home_win_odds_diff

    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
        ),
        "season": year,
        "round_number": 1,
        "round": f"{year} Round 1",
        "home_team": team_names[0],
        "away_team": team_names[1],
        "home_score": home_score,
        "away_score": away_score,
        "home_margin": home_score - away_score,
        "away_margin": away_score - home_score,
        "home_win_odds": home_win_odds,
        "away_win_odds": away_win_odds,
        "home_win_paid": home_win_odds * int(home_score > away_score),
        "away_win_paid": away_win_odds * int(away_score > home_score),
        "home_line_odds": home_line_odds,
        "away_line_odds": -1 * home_line_odds,
        "home_line_paid": BASELINE_BET_PAYOUT * int(home_score > away_score),
        "away_line_paid": BASELINE_BET_PAYOUT * int(away_score > home_score),
        "venue": FAKE.city(),
    }


def _betting_by_round(row_count: int, year: int):
    team_names = CyclicalTeamNames()

    return [
        _betting_data(year, (team_names.next(), team_names.next()))
        for idx in range(row_count)
    ]


def _betting_by_year(row_count: int, year_range: Tuple[int, int]):
    return [_betting_by_round(row_count, year) for year in range(*year_range)]


def fake_footywire_betting_data(
    row_count: int, year_range: Tuple[int, int]
) -> pd.DataFrame:
    data = _betting_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    return pd.DataFrame(list(reduced_data))


def fake_prediction_data(
    match_data: Union[CleanFixtureData, Match, None] = None,
    ml_model_name="test_estimator",
) -> pd.DataFrame:
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

    predictions = [
        {
            "team": match_data_for_pred["home_team"],
            "year": match_data_for_pred["year"],
            "round_number": match_data_for_pred["round_number"],
            "at_home": 1,
            "oppo_team": match_data_for_pred["away_team"],
            "ml_model": ml_model_name,
            "predicted_margin": np.random.rand() * 50,
        },
        {
            "team": match_data_for_pred["away_team"],
            "year": match_data_for_pred["year"],
            "round_number": match_data_for_pred["round_number"],
            "at_home": 0,
            "oppo_team": match_data_for_pred["home_team"],
            "ml_model": ml_model_name,
            "predicted_margin": np.random.rand() * 50,
        },
    ]

    return pd.DataFrame(predictions)
