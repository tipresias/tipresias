from typing import List, Dict, Any, Tuple
from datetime import datetime
import itertools
from faker import Faker
import numpy as np
import pandas as pd

from machine_learning.data_config import TEAM_NAMES, DEFUNCT_TEAM_NAMES
from server.types import RawFixtureData, MatchData
from project.settings.common import MELBOURNE_TIMEZONE

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


def _match_data(year: int, team_names: Tuple[str, str]) -> MatchData:
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
    }


def _match_by_round(row_count: int, year: int) -> List[MatchData]:
    team_names = CyclicalTeamNames()

    return [
        _match_data(year, (team_names.next(), team_names.next()))
        for idx in range(row_count)
    ]


def _match_by_year(
    row_count: int, year_range: Tuple[int, int]
) -> List[List[MatchData]]:
    return [_match_by_round(row_count, year) for year in range(*year_range)]


def fake_match_results_data(
    row_count: int, year_range: Tuple[int, int]
) -> pd.DataFrame:
    data = _match_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    return pd.DataFrame(list(reduced_data))


def _fixture_data(year: int, team_names: Tuple[str, str]) -> RawFixtureData:
    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
        ),
        "season": year,
        "round": 1,
        "home_team": team_names[0],
        "away_team": team_names[1],
        "venue": FAKE.city(),
    }


def _fixture_by_round(row_count: int, year: int) -> List[RawFixtureData]:
    team_names = CyclicalTeamNames()

    return [
        _fixture_data(year, (team_names.next(), team_names.next()))
        for idx in range(row_count)
    ]


def _fixture_by_year(
    row_count: int, year_range: Tuple[int, int]
) -> List[List[RawFixtureData]]:
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
