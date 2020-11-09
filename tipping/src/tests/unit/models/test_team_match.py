# pylint: disable=missing-docstring

from unittest.mock import patch

import pytest
from faker import Faker
import numpy as np

from tests.fixtures.factories import TeamFactory, MatchFactory, TeamMatchFactory
from tipping.models.team_match import ValidationError


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
@patch("tipping.models.team_match.FaunadbClient.graphql")
def test_saving_invalid_team(mock_graphql, invalid_attribute, error_message):
    team_match = TeamMatchFactory.build(
        team__add_id=True, match__add_id=True, **invalid_attribute
    )

    # It raises a ValidationError
    with pytest.raises(ValidationError, match=error_message):
        team_match.save()

    # It doesn't save the team
    mock_graphql.assert_not_called()
