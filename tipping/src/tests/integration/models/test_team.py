# pylint: disable=missing-docstring

import pytest

from tests.fixtures.factories import TeamFactory
from tipping.db.faunadb import GraphQLError
from tipping.models import Team


def test_saving_valid_team(faunadb_client):
    team = TeamFactory.build()
    saved_team = team.create()

    # It returns the saved team
    assert saved_team == team

    # It saves the team in the DB
    query = "query { findTeamByID(id: %s) { _id } }" % (saved_team.id)
    result = faunadb_client.graphql(query)
    assert result["findTeamByID"]["_id"]


def test_saving_duplicate_team(faunadb_client):  # pylint: disable=unused-argument
    saved_team = TeamFactory.create()
    new_team = TeamFactory.build(name=saved_team.name)

    # It raises an error
    with pytest.raises(GraphQLError, match=r"Instance is not unique"):
        new_team.create()


def test_finding_by_name(faunadb_client):  # pylint: disable=unused-argument
    team = TeamFactory.create()

    found_team = Team.find_by(name=team.name)

    # It finds the correct team
    assert team.name == found_team.name
