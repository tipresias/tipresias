# pylint: disable=missing-docstring

from unittest.mock import patch

import pytest

from tests.fixtures.factories import TeamFactory
from tipping.models.team import ValidationError


@pytest.mark.parametrize(
    ["team_name", "error_message"],
    [
        ("", "empty values not allowed"),
        (None, "null value not allowed"),
        (42, "string"),
    ],
)
@patch("tipping.models.team.FaunadbClient.graphql")
def test_saving_invalid_team(mock_graphql, team_name, error_message):
    team = TeamFactory.build(name=team_name)

    # It raises a ValidateionError
    with pytest.raises(ValidationError, match=error_message):
        team.save()

    # It doesn't save the team
    mock_graphql.assert_not_called()
