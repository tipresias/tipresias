# pylint: disable=missing-docstring,redefined-outer-name

from sqlalchemy.orm import sessionmaker
import numpy as np

from tipping.models.team import Team, TeamName


def test_team_creation(fauna_engine):
    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    team_name = np.random.choice(TeamName.values())
    team = Team(name=team_name)
    session.add(team)
    session.commit()

    assert team.id is not None
