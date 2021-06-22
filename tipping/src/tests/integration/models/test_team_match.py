# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import numpy as np
from faker import Faker
import pytest
from sqlalchemy import select

from tests.fixtures import data_factories
from tipping.models import TeamMatch, Team, Match
from tipping.models.team import TeamName


FAKE = Faker()


@pytest.fixture
def match():
    return Match(
        start_date_time=FAKE.date_time(tzinfo=timezone.utc),
        round_number=np.random.randint(1, 100),
        venue=FAKE.company(),
    )


def test_team_match_creation(fauna_session, match):
    team_name = np.random.choice(TeamName.values())
    team = (
        fauna_session.execute(select(Team).where(Team.name == team_name))
        .scalars()
        .one()
    )
    fauna_session.add(match)
    fauna_session.commit()

    team_match = TeamMatch(
        team_id=team.id,
        match_id=match.id,
        at_home=FAKE.pybool(),
        score=np.random.randint(0, 100),
    )
    fauna_session.add(team_match)
    fauna_session.commit()

    assert team_match.id is not None
    assert team_match.team.id == team.id
    assert team_match.match.id == match.id
    assert match.team_matches[0].score == team_match.score


def test_from_fixture(fauna_session):
    fixture_matches = data_factories.fake_fixture_data()
    next_match = fixture_matches.iloc[np.random.randint(0, len(fixture_matches)), :]

    team_matches = TeamMatch.from_fixture(fauna_session, next_match)

    for team_match in team_matches:
        if team_match.at_home:
            assert team_match.team.name == next_match["home_team"]
        else:
            assert team_match.team.name == next_match["away_team"]
