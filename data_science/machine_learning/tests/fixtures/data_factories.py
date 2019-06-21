from typing import List, Dict, Tuple, Any
from datetime import datetime
import itertools
from faker import Faker
import numpy as np
import pandas as pd

from machine_learning.data_config import TEAM_NAMES, DEFUNCT_TEAM_NAMES
from machine_learning.types import CleanedMatchData
from machine_learning.data_config import INDEX_COLS
from settings import MELBOURNE_TIMEZONE

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


def _match_data(year: int, team_names: Tuple[str, str], idx: int) -> CleanedMatchData:
    return {
        "date": FAKE.date_time_between_dates(
            **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
        ),
        "year": year,
        "round_number": round(idx / (len(CONTEMPORARY_TEAM_NAMES) / 2)) + 1,
        "team": team_names[0],
        "oppo_team": team_names[1],
        "score": np.random.randint(50, 150),
        "oppo_score": np.random.randint(50, 150),
    }


def _matches_by_round(match_count_per_year: int, year: int) -> List[CleanedMatchData]:
    team_names = CyclicalTeamNames()

    return [
        _match_data(year, (team_names.next(), team_names.next()), idx)
        for idx in range(match_count_per_year)
    ]


def _matches_by_year(
    match_count_per_year: int, year_range: Tuple[int, int]
) -> List[List[CleanedMatchData]]:
    return [
        _matches_by_round(match_count_per_year, year) for year in range(*year_range)
    ]


def _oppo_match_data(team_match: CleanedMatchData) -> CleanedMatchData:
    return {
        # mypy isn't smart enough to to interpret **{}-style dict composition
        **team_match,  # type: ignore
        **{
            "team": team_match["oppo_team"],
            "oppo_team": team_match["team"],
            "score": team_match["oppo_score"],
            "oppo_score": team_match["score"],
        },
    }


def _add_oppo_rows(match_data: List[CleanedMatchData]):
    data = [[match, _oppo_match_data(match)] for match in match_data]

    return list(itertools.chain.from_iterable(data))


def fake_cleaned_match_data(
    match_count_per_year: int, year_range: Tuple[int, int], oppo_rows: bool = True
) -> pd.DataFrame:
    data = _matches_by_year(match_count_per_year, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    if oppo_rows:
        data_frame = pd.DataFrame(_add_oppo_rows(reduced_data))
    else:
        data_frame = pd.DataFrame(reduced_data)

    return data_frame.set_index(INDEX_COLS, drop=False).rename_axis(
        [None] * len(INDEX_COLS)
    )


def _players_by_match(
    match_data: CleanedMatchData, n_players: int, idx: int
) -> List[Dict[str, Any]]:
    # Assumes that both team and oppo_team rows are present and that they alternate
    # in order to evenly split players between the two
    playing_for = match_data["team"] if idx % 2 == 0 else match_data["oppo_team"]

    return [
        {
            **match_data,
            **{
                "player_id": FAKE.ean(),
                "player_name": FAKE.name(),
                "playing_for": playing_for,
            },
        }
        for _ in range(n_players)
    ]


def fake_cleaned_player_data(
    match_count_per_year: int, year_range: Tuple[int, int], n_players_per_team: int
) -> pd.DataFrame:
    match_data = _matches_by_year(match_count_per_year, year_range)
    reduced_match_data = list(itertools.chain.from_iterable(match_data))

    player_data = [
        _players_by_match(match_data, n_players_per_team, idx)
        for idx, match_data in enumerate(_add_oppo_rows(reduced_match_data))
    ]
    reduced_player_data = list(itertools.chain.from_iterable(player_data))

    return pd.DataFrame(reduced_player_data)
