from typing import List, Dict, Tuple, Any, Union, cast
from datetime import datetime
import itertools

from faker import Faker
import numpy as np
import pandas as pd
from mypy_extensions import TypedDict

from machine_learning.data_config import TEAM_NAMES, DEFUNCT_TEAM_NAMES
from machine_learning.data_config import INDEX_COLS
from machine_learning.settings import MELBOURNE_TIMEZONE


BettingData = TypedDict(
    "BettingData",
    {
        "date": datetime,
        "season": int,
        "round_number": int,
        "round": str,
        "home_team": str,
        "away_team": str,
        "home_score": int,
        "away_score": int,
        "home_margin": int,
        "away_margin": int,
        "home_win_odds": float,
        "away_win_odds": float,
        "home_win_paid": float,
        "away_win_paid": float,
        "home_line_odds": float,
        "away_line_odds": float,
        "home_line_paid": float,
        "away_line_paid": float,
        "venue": str,
    },
)

CleanFixtureData = TypedDict(
    "CleanFixtureData",
    {
        "date": datetime,
        "season": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)

CleanedMatchData = TypedDict(
    "CleanedMatchData",
    {
        "date": datetime,
        "year": int,
        "round_number": int,
        "team": str,
        "oppo_team": str,
        "score": int,
        "oppo_score": int,
    },
)

MatchData = TypedDict(
    "MatchData",
    {
        "date": Union[datetime, pd.Timestamp],
        "season": int,
        "round": str,
        "round_number": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
        "home_score": int,
        "away_score": int,
        "match_id": int,
        "crowd": int,
    },
)

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


def _raw_match_data(year: int, team_names: Tuple[str, str], idx: int) -> MatchData:
    return cast(
        MatchData,
        {
            "date": FAKE.date_time_between_dates(
                **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
            ),
            "season": year,
            "round": "R1",
            "round_number": round(idx / (len(CONTEMPORARY_TEAM_NAMES) / 2)) + 1,
            "home_team": team_names[0],
            "away_team": team_names[1],
            "venue": FAKE.city(),
            "home_score": np.random.randint(50, 150),
            "away_score": np.random.randint(50, 150),
            "match_id": FAKE.ean(),
            "crowd": np.random.randint(10000, 30000),
        },
    )


def _match_data(year: int, team_names: Tuple[str, str], idx: int) -> CleanedMatchData:
    return cast(
        CleanedMatchData,
        {
            "date": FAKE.date_time_between_dates(
                **_min_max_datetimes_by_year(year), tzinfo=MELBOURNE_TIMEZONE
            ),
            "year": year,
            "round_number": round(idx / (len(CONTEMPORARY_TEAM_NAMES) / 2)) + 1,
            "team": team_names[0],
            "oppo_team": team_names[1],
            "score": np.random.randint(50, 150),
            "oppo_score": np.random.randint(50, 150),
        },
    )


def _matches_by_round(
    match_count_per_year: int, year: int, raw=False
) -> Union[List[CleanedMatchData], List[MatchData]]:
    team_names = CyclicalTeamNames()

    if raw:
        return [
            _raw_match_data(year, (team_names.next(), team_names.next()), idx)
            for idx in range(match_count_per_year)
        ]

    return [
        _match_data(year, (team_names.next(), team_names.next()), idx)
        for idx in range(match_count_per_year)
    ]


def _matches_by_year(
    match_count_per_year: int, year_range: Tuple[int, int], raw=False
) -> List[Union[List[CleanedMatchData], List[MatchData]]]:
    return [
        _matches_by_round(match_count_per_year, year, raw=raw)
        for year in range(*year_range)
    ]


def _oppo_match_data(team_match: CleanedMatchData) -> CleanedMatchData:
    return cast(
        CleanedMatchData,
        {
            **team_match,
            **{
                "team": team_match["oppo_team"],
                "oppo_team": team_match["team"],
                "score": team_match["oppo_score"],
                "oppo_score": team_match["score"],
            },
        },
    )


def _add_oppo_rows(match_data: List[CleanedMatchData]) -> List[CleanedMatchData]:
    data = [[match, _oppo_match_data(match)] for match in match_data]

    return list(itertools.chain.from_iterable(data))


def fake_cleaned_match_data(
    match_count_per_year: int, year_range: Tuple[int, int], oppo_rows: bool = True
) -> pd.DataFrame:
    data = cast(
        List[List[CleanedMatchData]], _matches_by_year(match_count_per_year, year_range)
    )
    reduced_data = list(itertools.chain.from_iterable(data))

    if oppo_rows:
        data_frame = pd.DataFrame(_add_oppo_rows(reduced_data))
    else:
        data_frame = pd.DataFrame(reduced_data)

    return data_frame.set_index(INDEX_COLS, drop=False).rename_axis(
        [None] * len(INDEX_COLS)
    )


def fake_raw_match_results_data(
    row_count: int, year_range: Tuple[int, int], clean=False
) -> pd.DataFrame:
    data = cast(
        List[List[MatchData]], _matches_by_year(row_count, year_range, raw=True)
    )
    reduced_data = list(itertools.chain.from_iterable(data))
    data_frame = pd.DataFrame(list(reduced_data))

    if clean:
        return data_frame.rename(columns={"season": "year"})

    return data_frame


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
    match_data = cast(
        List[List[CleanedMatchData]], _matches_by_year(match_count_per_year, year_range)
    )
    reduced_match_data = list(itertools.chain.from_iterable(match_data))

    player_data = [
        _players_by_match(match_data, n_players_per_team, idx)
        for idx, match_data in enumerate(_add_oppo_rows(reduced_match_data))
    ]
    reduced_player_data = list(itertools.chain.from_iterable(player_data))

    return pd.DataFrame(reduced_player_data)


def _betting_data(year: int, team_names: Tuple[str, str]) -> BettingData:
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


def _betting_by_round(row_count: int, year: int) -> List[BettingData]:
    team_names = CyclicalTeamNames()

    return [
        _betting_data(year, (team_names.next(), team_names.next()))
        for idx in range(row_count)
    ]


def _betting_by_year(
    row_count: int, year_range: Tuple[int, int]
) -> List[List[BettingData]]:
    return [_betting_by_round(row_count, year) for year in range(*year_range)]


def fake_footywire_betting_data(
    row_count: int, year_range: Tuple[int, int]
) -> pd.DataFrame:
    data = _betting_by_year(row_count, year_range)
    reduced_data = list(itertools.chain.from_iterable(data))

    return pd.DataFrame(list(reduced_data))


def _fixture_data(year: int, team_names: Tuple[str, str]) -> CleanFixtureData:
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
