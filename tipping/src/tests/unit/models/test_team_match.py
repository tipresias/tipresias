# pylint: disable=missing-docstring

from unittest.mock import patch, MagicMock

import pytest
from faker import Faker
import numpy as np

from tests.fixtures.factories import TeamFactory, MatchFactory, TeamMatchFactory
from tests.fixtures.data_factories import fake_fixture_data
from tests.helpers.model_helpers import assert_deep_equal_attributes
from tipping.models.base_model import ValidationError
from tipping.models import TeamMatch


FAKE = Faker()

BIG_NUMBER = 999
TYPICAL_MAX_ROUND = 27


@pytest.mark.parametrize(
    ["invalid_attribute", "error_message"],
    [
        ({"score": np.random.randint(-BIG_NUMBER, -1)}, "min value is 0"),
        ({"at_home": None}, "null value not allowed"),
        ({"team": TeamFactory.build()}, "must have an ID"),
        ({"match": MatchFactory.build()}, "must have an ID"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_saving_invalid_team_match(mock_graphql, invalid_attribute, error_message):
    team_match = TeamMatchFactory.build(
        team__add_id=True, match__add_id=True, **invalid_attribute
    )

    # It raises a ValidationError
    with pytest.raises(ValidationError, match=error_message):
        team_match.create()

    # It doesn't save the team_match
    mock_graphql.assert_not_called()


def test_from_db_response():
    team = TeamFactory.build(add_id=True)
    match = MatchFactory.build(add_id=True)
    team_match = TeamMatchFactory.build(team=team, match=match, add_id=True)
    db_record = {
        "team": {"name": team.name, "_id": team.id},
        "match": {
            "startDateTime": match.start_date_time.isoformat(),
            "season": match.season,
            "roundNumber": match.round_number,
            "venue": match.venue,
            "margin": match.margin,
            "winner": None
            if match.winner is None
            else {"name": match.winner.name, "_id": match.winner.id},
            "_id": match.id,
        },
        "atHome": team_match.at_home,
        "score": team_match.score,
        "_id": team_match.id,
    }

    team_match_from_record = TeamMatch.from_db_response(db_record)

    # It returns a match object
    assert isinstance(team_match_from_record, TeamMatch)

    # It has matching attributes
    assert_deep_equal_attributes(team_match, team_match_from_record)


@patch(
    "tipping.models.team.Team.find_by",
    MagicMock(return_value=TeamFactory.build(add_id=True)),
)
def test_from_raw_data():
    fixture = fake_fixture_data().iloc[0, :]
    team_matches = TeamMatch.from_raw_data(fixture)

    # It returns two objects
    assert len(team_matches) == 2

    # It returns TeamMatch objects
    for team_match in team_matches:
        isinstance(team_match, TeamMatch)

    # It returns one home TeamMatch and one away
    home_team_matches = [
        team_match for team_match in team_matches if team_match.at_home
    ]
    assert len(home_team_matches) == 1

    away_team_matches = [
        team_match for team_match in team_matches if not team_match.at_home
    ]
    assert len(away_team_matches) == 1
