# pylint: disable=missing-docstring

import pytest

from tests.fixtures.factories import TeamFactory
from tipping.db.faunadb import GraphQLError


def test_saving_valid_team(faunadb_client):
    team = TeamFactory.build()
    saved_team = team.save()

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
        new_team.save()
