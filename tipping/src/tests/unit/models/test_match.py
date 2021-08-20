# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone, datetime, timedelta
from unittest import mock

import pytest
from faker import Faker
import numpy as np

from tests.fixtures import data_factories
from tipping import models
from tipping.models.match import Match, ValidationError
from tipping.models.team import TeamName


Fake = Faker()


@pytest.mark.parametrize(
    "attribute,error_message",
    [
        ({"round_number": np.random.randint(-100, 1)}, r"round_number"),
        ({"margin": np.random.randint(-100, 0)}, r"margin"),
        ({"start_date_time": Fake.date_time()}, r"start_date_time"),
    ],
)
def test_match_validation(attribute, error_message):
    default_input = {
        "start_date_time": Fake.date_time(tzinfo=timezone.utc),
        "venue": Fake.street_name(),
        "margin": np.random.randint(0, 100),
        "round_number": np.random.randint(1, 100),
    }

    with pytest.raises(ValidationError, match=error_message):
        Match(
            **{
                **default_input,
                **attribute,
            }
        )


@mock.patch("tipping.models.match.Match.update_result")
def test_update_results(mock_update_result):
    match_results = data_factories.fake_match_results_data()
    calls = []
    matches = []

    for _idx, match_result in match_results.iterrows():
        home_team = models.Team(name=match_result["home_team"])
        match = Match(
            start_date_time=match_result["date"],
            venue=Fake.company(),
            round_number=match_result["round_number"],
            team_matches=[
                models.TeamMatch(
                    team=home_team,
                    at_home=True,
                ),
                models.TeamMatch(
                    team=models.Team(name=match_result["away_team"]),
                    at_home=False,
                ),
            ],
            predictions=[
                models.Prediction(
                    ml_model=models.MLModel(
                        name=Fake.company(), prediction_type="margin"
                    ),
                    predicted_winner=home_team,
                    predicted_margin=np.random.randint(0, 100),
                )
            ],
        )
        matches.append(match)
        calls.append(mock.call(match_result))

    Match.update_results(matches, match_results)

    assert mock_update_result.call_count == len(match_results)


@pytest.mark.parametrize(
    ["start_date_time", "expected_winner"],
    [
        (
            datetime.now(tz=timezone.utc) - timedelta(days=1),
            np.random.choice(TeamName.values()),
        ),
        (datetime.now(tz=timezone.utc), None),
        (datetime.now(tz=timezone.utc) + timedelta(days=1), None),
    ],
)
def test_update_result(start_date_time, expected_winner):
    match_results = data_factories.fake_match_results_data()
    home_team_name = expected_winner or np.random.choice(TeamName.values())
    home_team = models.Team(name=home_team_name)
    home_team_results = match_results.query("home_team == @home_team_name")
    random_row_idx = np.random.randint(0, len(home_team_results))
    match_result = home_team_results.iloc[random_row_idx : (random_row_idx + 1), :]
    match_result["home_score"] = match_result["away_score"] * 2
    match = Match(
        start_date_time=start_date_time,
        venue=Fake.company(),
        round_number=np.random.randint(1, 100),
        team_matches=[
            models.TeamMatch(
                team=home_team,
                at_home=True,
            ),
            models.TeamMatch(
                team=models.Team(name=match_result.iloc[0, :]["away_team"]),
                at_home=False,
            ),
        ],
        predictions=[
            models.Prediction(
                ml_model=models.MLModel(name=Fake.company(), prediction_type="margin"),
                predicted_winner=home_team,
                predicted_margin=np.random.randint(0, 100),
            )
        ],
    )

    match.update_result(match_result)

    if expected_winner is None:
        assert match.margin is None
        assert match.winner is None
        for team_match in match.team_matches:
            assert team_match.score is None
        for prediction in match.predictions:
            assert prediction.is_correct is None
    else:
        assert match.margin == abs(
            match_result.iloc[0, :]["home_score"]
            - match_result.iloc[0, :]["away_score"]
        )
        assert match.winner.name == home_team.name
        for team_match in match.team_matches:
            assert team_match.score is not None
        for prediction in match.predictions:
            assert prediction.is_correct is not None
