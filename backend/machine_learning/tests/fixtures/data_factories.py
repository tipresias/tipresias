from typing import List, Dict, Tuple
from datetime import datetime
import itertools
from faker import Faker
import numpy as np
import pandas as pd

from machine_learning.data_config import TEAM_NAMES, DEFUNCT_TEAM_NAMES
from machine_learning.types import CleanedMatchData
from machine_learning.data_config import INDEX_COLS


FIRST = 1
SECOND = 2
JAN = 1
DEC = 12
THIRTY_FIRST = 31
FAKE = Faker()
CONTEMPORARY_TEAM_NAMES = [
    name for name in TEAM_NAMES if name not in DEFUNCT_TEAM_NAMES
]


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


def _match_data(year: int, team_names: Tuple[str, str]) -> CleanedMatchData:
    return {
        "date": FAKE.date_time_between_dates(**_min_max_datetimes_by_year(year)),
        "year": year,
        "round_number": 1,
        "team": team_names[0],
        "oppo_team": team_names[1],
        "score": np.random.randint(50, 150),
        "oppo_score": np.random.randint(50, 150),
    }


def _matches_by_round(round_count: int, year: int) -> List[CleanedMatchData]:
    team_names = CyclicalTeamNames()

    return [
        _match_data(year, (team_names.next(), team_names.next()))
        for idx in range(round_count)
    ]


def _matches_by_year(
    round_count: int, year_range: Tuple[int, int]
) -> List[List[CleanedMatchData]]:
    return [_matches_by_round(round_count, year) for year in range(*year_range)]


def fake_cleaned_match_data(
    round_count: int, year_range: Tuple[int, int]
) -> pd.DataFrame:
    data = _matches_by_year(round_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    return (
        pd.DataFrame(list(reduced_data))
        .set_index(INDEX_COLS, drop=False)
        .rename_axis([None] * len(INDEX_COLS))
    )
