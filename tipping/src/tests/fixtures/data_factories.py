"""Module for factory functions that create raw data objects."""

from typing import List, Tuple, Union, Optional
from datetime import timedelta

from faker import Faker
import numpy as np
import pandas as pd
from candystore import CandyStore

from tipping import settings
from tipping.types import FixtureData


FAKE = Faker()
CONTEMPORARY_TEAM_NAMES = [
    name for name in settings.TEAM_NAMES if name not in settings.DEFUNCT_TEAM_NAMES
]
DEFAULT_YEAR_RANGE = (2015, 2016)

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


class CyclicalTeamNames:
    """Cycles through real team names per data config."""

    def __init__(self, team_names: List[str] = CONTEMPORARY_TEAM_NAMES):
        """
        Instantiate a CyclicalTeamNames object.

        Params:
        -------
        team_names: List of team names to cycle through. Defaults to all teams
            currently in the AFL.
        """
        self.team_names = team_names
        self.cyclical_team_names = (name for name in self.team_names)

    def next_team(self) -> str:
        """Return the next team name or start over from the beginning."""
        try:
            return next(self.cyclical_team_names)
        except StopIteration:
            self.cyclical_team_names = (name for name in self.team_names)

            return next(self.cyclical_team_names)


def fake_match_data(year_range: Tuple[int, int]) -> pd.DataFrame:
    """Return minimally-valid dummy match results data."""
    return (
        CandyStore(seasons=year_range)
        .match_results(to_dict=None)
        .rename(
            columns={
                "season": "year",
                "home_points": "home_score",
                "away_points": "away_score",
            }
        )
    )


def fake_fixture_data(year_range: Tuple[int, int]) -> List[FixtureData]:
    """
    Return minimally-valid data for fixture data.

    These matches are usually unplayed, future matches, but it is also possible to get
    data for past fixtures.
    """
    return (
        CandyStore(seasons=year_range)
        .fixtures(to_dict=None)
        .rename(columns={"season": "year", "round": "round_number"})
        .drop("season_game", axis=1)
        # Recreates data cleaning performed in views.fixtures
        .assign(date=lambda df: pd.to_datetime(df["date"], utc=True))
        .to_dict("records")
    )


def fake_match_results_data(
    match_data: Optional[pd.DataFrame] = None, round_number: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate dummy data that replicates match results data.

    Params
    ------
    match_data: Match data on which to base the match results data set.
    round_number: Round number to use for match results data (because it's fetched
        one round at a time).

    Returns
    -------
    DataFrame of match results data
    """
    match_data = match_data or fake_match_data(DEFAULT_YEAR_RANGE)
    round_number = round_number or np.random.randint(
        1, match_data["round_number"].max()
    )

    assert (
        len(match_data["year"].drop_duplicates()) == 1
    ), "Match results data is fetched one season at a time."

    return (
        match_data.query("round_number == @round_number")
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


def fake_prediction_data(
    match_data: Union[FixtureData, None] = None,
    ml_model_name="test_estimator",
    predict_margin=True,
) -> pd.DataFrame:
    """Return minimally-valid prediction data."""
    if match_data is None:
        match_data_for_pred = fake_fixture_data((2018, 2019))[0]
    else:
        match_data_for_pred = match_data

    predicted_home_margin = np.random.rand() * 50 if predict_margin else None
    predicted_away_margin = np.random.rand() * 50 if predict_margin else None
    predicted_home_proba = np.random.rand() if not predict_margin else None
    predicted_away_proba = np.random.rand() if not predict_margin else None

    predictions = [
        {
            "team": match_data_for_pred["home_team"],
            "year": match_data_for_pred["year"],
            "round_number": match_data_for_pred["round_number"],
            "at_home": 1,
            "oppo_team": match_data_for_pred["away_team"],
            "ml_model": ml_model_name,
            "predicted_margin": predicted_home_margin,
            "predicted_win_probability": predicted_home_proba,
        },
        {
            "team": match_data_for_pred["away_team"],
            "year": match_data_for_pred["year"],
            "round_number": match_data_for_pred["round_number"],
            "at_home": 0,
            "oppo_team": match_data_for_pred["home_team"],
            "ml_model": ml_model_name,
            "predicted_margin": predicted_away_margin,
            "predicted_win_probability": predicted_away_proba,
        },
    ]

    return pd.DataFrame(predictions)


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
