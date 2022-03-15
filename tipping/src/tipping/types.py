"""Collection of TypedDicts for static typing."""

import typing
from datetime import datetime

from mypy_extensions import TypedDict
from pandas import Timestamp


MatchPrediction = TypedDict(
    "MatchPrediction",
    {
        "predicted_winner__name": str,
        "predicted_margin": float,
        "predicted_win_probability": float,
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
        "home_predicted_margin": typing.Optional[float],
        "away_predicted_margin": typing.Optional[float],
        "home_predicted_win_probability": typing.Optional[float],
        "away_predicted_win_probability": typing.Optional[float],
    },
)


MatchData = TypedDict(
    "MatchData",
    {
        "date": typing.Union[datetime, Timestamp],
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
        "prediction_type": typing.Union[
            typing.Literal["margin"], typing.Literal["win_probability"]
        ],
        "trained_to": int,
        "data_set": typing.Union[
            typing.Literal["legacy_model_data"], typing.Literal["model_data"]
        ],
        "label_col": typing.Union[typing.Literal["margin"], typing.Literal["result"]],
    },
)

FixtureData = TypedDict(
    "FixtureData",
    {
        "date": datetime,
        "year": int,
        "round_number": int,
        "home_team": str,
        "away_team": str,
        "venue": str,
    },
)
