"""Collection of TypedDicts for static typing."""

from typing import Union, Literal
from datetime import datetime

from mypy_extensions import TypedDict
from pandas import Timestamp

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
        "home_predicted_win_probability": float,
        "away_predicted_win_probability": float,
    },
)

MatchData = TypedDict(
    "MatchData",
    {
        "date": Union[datetime, Timestamp],
        "year": int,
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

MLModelInfo = TypedDict(
    "MLModelInfo",
    {
        "name": str,
        "prediction_type": Union[Literal["margin"], Literal["win_probability"]],
        "trained_to": int,
        "data_set": Union[Literal["legacy_model_data"], Literal["model_data"]],
        "label_col": Union[Literal["margin"], Literal["result"]],
    },
)
