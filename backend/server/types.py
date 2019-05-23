from typing import Union
from datetime import datetime
from mypy_extensions import TypedDict
from pandas import Timestamp

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": Union[datetime],
        "season": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)

MatchData = TypedDict(
    "MatchData",
    {
        "date": Union[datetime, Timestamp],
        "season": int,
        "round": str,
        "round_number": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
        "home_score": int,
        "away_score": int,
    },
)
