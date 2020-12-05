# pylint: disable=missing-docstring

from unittest.mock import patch

import pytest

from tests.fixtures.factories import TeamFactory
from tipping.models.base_model import ValidationError
from tipping.models import Team


@pytest.mark.parametrize(
    ["team_name", "error_message"],
    [
        ("", "empty values not allowed"),
        (None, "null value not allowed"),
        (42, "string"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_saving_invalid_team(mock_graphql, team_name, error_message):
    team = TeamFactory.build(name=team_name)

    # It raises a ValidateionError
    with pytest.raises(ValidationError, match=error_message):
        team.create()

    # It doesn't save the team
    mock_graphql.assert_not_called()


def test_from_db_response():
    team = TeamFactory.build(add_id=True)
    db_record = {"name": team.name, "_id": team.id}

    team_from_record = Team.from_db_response(db_record)

    # It returns a team object
    assert isinstance(team_from_record, Team)

    # It has matching attributes
    assert team.attributes == team_from_record.attributes
