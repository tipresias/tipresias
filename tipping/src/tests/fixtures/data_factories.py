"""Module for factory functions that create raw data objects."""

from typing import Tuple, Union, Optional
from datetime import timedelta

from faker import Faker
import numpy as np
import pandas as pd
from candystore import CandyStore

from tipping import settings


FAKE = Faker()

MATCH_RESULTS_COLS = [
    "date",
    "tz",
    "updated",
    "round",
    "roundname",
    "year",
    "hbehinds",
    "hgoals",
    "hscore",
    "hteam",
    "hteamid",
    "abehinds",
    "agoals",
    "ascore",
    "ateam",
    "ateamid",
    "winner",
    "winnerteamid",
    "is_grand_final",
    "complete",
    "is_final",
    "id",
    "venue",
]

TEAM_TYPES = ("home", "away")


def fake_match_data(
    match_results: Optional[pd.DataFrame] = None,
    seasons: Union[Tuple[int, int], int] = 1,
) -> pd.DataFrame:
    """Return minimally-valid dummy match results data."""
    match_results = (
        CandyStore(seasons=seasons).match_results(to_dict=None)
        if match_results is None
        else match_results
    )

    return match_results.rename(
        columns={
            "season": "year",
            "home_points": "home_score",
            "away_points": "away_score",
        }
    )


def fake_fixture_data(
    fixtures: Optional[pd.DataFrame] = None,
    seasons: Union[Tuple[int, int], int] = 1,
) -> pd.DataFrame:
    """
    Return minimally-valid data for fixture data.

    These matches are usually unplayed, future matches, but it is also possible to get
    data for past fixtures.
    """
    fixtures = (
        CandyStore(seasons=seasons).fixtures(to_dict=None)
        if fixtures is None
        else fixtures
    )

    return (
        fixtures.rename(columns={"season": "year", "round": "round_number"}).drop(
            "season_game", axis=1, errors="ignore"
        )
        # Recreates data cleaning performed in views.fixtures
        .assign(date=lambda df: pd.to_datetime(df["date"], utc=True))
    )


def fake_match_results_data(
    match_results: Optional[pd.DataFrame] = None, round_number: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate dummy data that replicates match results data.

    Params
    ------
    match_results: Match data on which to base the match results data set.
    round_number: Round number to use for match results data (because it's fetched
        one round at a time).

    Returns
    -------
    DataFrame of match results data
    """
    match_results = fake_match_data() if match_results is None else match_results
    round_number = round_number or np.random.randint(
        1, match_results["round_number"].max()
    )

    assert (
        len(match_results["year"].drop_duplicates()) == 1
    ), "Match results data is fetched one season at a time."

    return (
        match_results.query("round_number == @round_number")
        .assign(
            updated=lambda df: pd.to_datetime(df["date"]) + timedelta(hours=3),
            tz="+10:00",
            # AFLTables match_results already have a 'round' column,
            # so we have to replace rather than rename.
            round=lambda df: df["round_number"],
            roundname=lambda df: "Round " + df["round_number"].astype(str),
            hteam=lambda df: df["home_team"].map(
                lambda team: settings.TEAM_TRANSLATIONS.get(team, team)
            ),
            ateam=lambda df: df["away_team"].map(
                lambda team: settings.TEAM_TRANSLATIONS.get(team, team)
            ),
            hteamid=lambda df: df["hteam"].map(settings.TEAM_NAMES.index),
            ateamid=lambda df: df["ateam"].map(settings.TEAM_NAMES.index),
            winner=lambda df: np.where(df["margin"] >= 0, df["hteam"], df["ateam"]),
            winnerteamid=lambda df: df["winner"].map(settings.TEAM_NAMES.index),
            is_grand_final=0,
            complete=100,
            is_final=0,
        )
        .astype({"updated": str})
        .reset_index(drop=False)
        .rename(
            columns={
                "index": "id",
                "home_behinds": "hbehinds",
                "home_goals": "hgoals",
                "away_behinds": "abehinds",
                "away_goals": "agoals",
                "home_score": "hscore",
                "away_score": "ascore",
            }
        )
    ).loc[:, MATCH_RESULTS_COLS]


def _build_team_matches(match_data: pd.DataFrame, team_type: str) -> pd.DataFrame:
    at_home = 1 if team_type == "home" else 0
    oppo_team_type = "away" if at_home else "home"
    team_match_data = {
        "team": match_data[f"{team_type}_team"],
        "at_home": at_home,
        "oppo_team": match_data[f"{oppo_team_type}_team"],
        "year": match_data["year"],
        "round_number": match_data["round_number"],
    }

    return pd.DataFrame(team_match_data)


def fake_prediction_data(
    fixtures: Optional[pd.DataFrame] = None,
    ml_model_name="test_estimator",
    predict_margin=True,
) -> pd.DataFrame:
    """
    Return minimally-valid prediction data.

    Params:
    -------
    fixtures: Fixture data to base predictions on. Random fixture data will be generated
        if missing.
    ml_model_name: Name of the MLModel making the predictions.
    predict_margin: Whether to predict the margin. Predicts win probability if false.

    Returns:
    --------
    Two predictions, one for each team, per match row.
    """
    fixture_data = fake_fixture_data(fixtures)
    match_count = len(fixture_data)

    return pd.concat(
        [_build_team_matches(fixture_data, team_type) for team_type in TEAM_TYPES]
    ).assign(
        predicted_margin=np.random.rand(match_count * 2) * 50
        if predict_margin
        else None,
        predicted_win_probability=None
        if predict_margin
        else np.random.rand(match_count * 2),
        ml_model=ml_model_name,
    )


def fake_ml_model_data(n_models: int = 1) -> pd.DataFrame:
    """Generate mock data for raw ML model info from the Augury app."""
    return pd.DataFrame(
        [
            {
                "name": FAKE.company(),
                "prediction_type": np.random.choice(["margin", "win_probability"]),
                "trained_to": FAKE.pybool(),
                "data_set": np.random.choice(["legacy_model_data", "model_data"]),
                "label_col": np.random.choice(["margin", "result"]),
            }
            for _ in range(n_models)
        ]
    )
