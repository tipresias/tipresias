# pylint: disable=missing-docstring,redefined-outer-name

import numpy as np

from tipping.models.team import Team, TeamName


def test_team_creation(fauna_session):
    team_name = np.random.choice(TeamName.values())
    team = Team(name=team_name)
    fauna_session.add(team)
    fauna_session.commit()

    assert team.id is not None
