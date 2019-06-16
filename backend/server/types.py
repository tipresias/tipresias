from typing import Union
from datetime import datetime
from mypy_extensions import TypedDict
from pandas import Timestamp

RawFixtureData = TypedDict(
    "RawFixtureData",
    {
        "date": Union[datetime],
        "season": int,
        "round": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)

CleanFixtureData = TypedDict(
    "CleanFixtureData",
    {
        "date": Union[datetime],
        "year": int,
        "round_number": int,
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
        "match_id": int,
    },
)

PredictionData = TypedDict(
    "PredictionData",
    {
        "team": str,
        "year": int,
        "round_number": int,
        "at_home": int,
        "oppo_team": str,
        "ml_model": str,
        "predicted_margin": float,
    },
)

CleanPredictionData = TypedDict(
    "CleanPredictionData",
    {
        "home_team": str,
        "year": int,
        "round_number": int,
        "away_team": str,
        "ml_model": str,
        "home_predicted_margin": float,
        "away_predicted_margin": float,
    },
)
