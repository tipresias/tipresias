# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

# from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

import numpy as np
from faker import Faker
import pytest

from tipping.models import TeamMatch, Team, Match
from tipping.models.team import TeamName


FAKE = Faker()


@pytest.fixture
def team():
    team_name = np.random.choice(TeamName.values())
    return Team(name=team_name)


@pytest.fixture
def match():
    return Match(
        start_date_time=FAKE.date_time(tzinfo=timezone.utc),
        round_number=np.random.randint(1, 100),
        venue=FAKE.company(),
    )


def test_team_match_creation(fauna_engine, team, match):
    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    session.add(team)
    session.add(match)
    session.commit()

    # team_id = session.execute(select(Team.id)).scalars().first()
    # match_id = session.execute(select(Match.id)).scalars().first()

    team_match = TeamMatch(
        team_id=team.id,
        match_id=match.id,
        at_home=FAKE.pybool(),
        score=np.random.randint(0, 100),
    )
    session.add(team_match)
    session.commit()

    assert team_match.id is not None
    assert team_match.team.id == team.id
    assert team_match.match.id == match.id
    assert match.team_matches[0].score == team_match.score
