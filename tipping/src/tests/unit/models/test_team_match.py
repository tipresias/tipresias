# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faker import Faker
import numpy as np

from tipping.models.team_match import TeamMatch, ValidationError


FAKE = Faker()


@pytest.mark.parametrize(
    "attribute,error_message",
    [
        ({"score": np.random.randint(-100, 0)}, r"score"),
    ],
)
def test_team_match_validation(attribute, error_message):
    default_input = {
        "team_id": np.random.randint(1, 100),
        "match_id": np.random.randint(1, 100),
        "score": np.random.randint(0, 100),
        "at_home": FAKE.pybool(),
    }

    with pytest.raises(ValidationError, match=error_message):
        TeamMatch(
            **{
                **default_input,
                **attribute,
            }
        )
