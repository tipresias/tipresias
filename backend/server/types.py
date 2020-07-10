"""Contains custom mypy TypedDicts that are used across the application."""

from typing import Union, Literal
from datetime import datetime

from mypy_extensions import TypedDict
from pandas import Timestamp


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
        "home_predicted_win_probability": float,
        "away_predicted_win_probability": float,
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

RoundMetrics = TypedDict(
    "RoundMetrics",
    {
        "match__start_date_time": datetime,
        "match__round_number": int,
        "ml_model__name": str,
        "predicted_margin": int,
        "predicted_win_probability": float,
        "predicted_winner__name": str,
        "ml_model__is_principal": bool,
        "ml_model__used_in_competitions": bool,
        "match__winner__name": str,
        "match__margin": int,
        "absolute_margin_diff": int,
        "bits": float,
        "cumulative_correct_count": int,
        "cumulative_accuracy": float,
        "cumulative_mean_absolute_error": float,
        "cumulative_margin_difference": int,
        "cumulative_bits": float,
    },
)
