# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faker import Faker
import numpy as np

from tests.fixtures import data_factories
from tipping import models
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


match_results = data_factories.fake_match_results_data()


def test_update_score():
    random_row_idx = np.random.randint(0, len(match_results))
    match_result = match_results.iloc[random_row_idx, :]
    team_match = TeamMatch(
        team=models.Team(name=match_result["home_team"]), at_home=True
    )

    team_match.update_score(match_result)

    assert team_match.score == match_result["home_score"]
