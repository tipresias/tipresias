# pylint: disable=missing-docstring,redefined-outer-name

import pytest

from tipping.models.team import Team, ValidationError


def test_team_name_validation():
    with pytest.raises(ValidationError, match=r"Team Team"):
        Team(name="Team Team")
