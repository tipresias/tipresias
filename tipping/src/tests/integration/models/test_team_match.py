# pylint: disable=missing-docstring,redefined-outer-name

import numpy as np
from faker import Faker

from tests.fixtures import data_factories, model_factories
from tipping.models import TeamMatch


Fake = Faker()


def test_team_match_creation(fauna_session):
    team = model_factories.TeamFactory()
    match = model_factories.MatchFactory()

    team_match = TeamMatch(
        team=team,
        match=match,
        at_home=Fake.pybool(),
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
