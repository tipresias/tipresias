# pylint: disable=missing-docstring

from unittest.mock import patch

import pytest
from faker import Faker

from tipping.models import Team
from tipping.db.faunadb import GraphQLError

FAKE = Faker()


@patch("tipping.models.team.FaunadbClient")
def test_saving_valid_team(mock_faunadb, faunadb_client):
    mock_faunadb.return_value = faunadb_client

    team_name = FAKE.company()
    team = Team(name=team_name)
    saved_team = team.save()

    # It returns the saved team
    assert saved_team == team

    # It saves the team in the DB
    query = "query { findTeamByID(id: %s) { _id } }" % (saved_team.id)
    result = faunadb_client.graphql(query)
    assert result["findTeamByID"]["_id"]


@patch("tipping.models.team.FaunadbClient")
def test_saving_duplicate_team(mock_faunadb, faunadb_client):
    mock_faunadb.return_value = faunadb_client

    team_name = FAKE.company()
    Team(name=team_name).save()
    team = Team(name=team_name)

    # It raises an error
    with pytest.raises(GraphQLError, match=r"Instance is not unique"):
        team.save()
