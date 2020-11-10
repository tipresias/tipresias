# pylint: disable=missing-docstring

from unittest.mock import patch

import pytest
from faker import Faker
import numpy as np

from tests.fixtures.factories import TeamFactory, MatchFactory
from tipping.models.base_model import ValidationError


FAKE = Faker()
BIG_NUMBER = 999


@pytest.mark.parametrize(
    ["invalid_attribute", "error_message"],
    [
        ({"start_date_time": FAKE.date_time()}, "must be set to the UTC timezone"),
        ({"season": np.random.randint(-BIG_NUMBER, 1)}, "min value is 1"),
        ({"round_number": np.random.randint(-BIG_NUMBER, 1)}, "min value is 1"),
        ({"venue": ""}, "empty values not allowed"),
        ({"winner": "Team Name"}, "must be of team type"),
        ({"winner": TeamFactory.build()}, "must have an ID"),
        ({"margin": np.random.randint(-BIG_NUMBER, 0)}, "min value is 0"),
    ],
)
@patch("tipping.models.base_model.FaunadbClient.graphql")
def test_saving_invalid_match(mock_graphql, invalid_attribute, error_message):
    match = MatchFactory.build(**invalid_attribute)

    # It raises a ValidateionError
    with pytest.raises(ValidationError, match=error_message):
        match.create()

    # It doesn't save the match
    mock_graphql.assert_not_called()
