# pylint: disable=missing-docstring

from datetime import date


from tests.fixtures.factories import MatchFactory, TeamFactory
from tipping.models import Match


def test_creating_valid_match(faunadb_client):
    winner = TeamFactory.create()
    match = MatchFactory.build(winner=winner)
    saved_match = match.create()

    # It returns the saved match
    assert saved_match == match

    # It saves the match in the DB
    query = "query { findMatchByID(id: %s) { _id } }" % (saved_match.id)
    result = faunadb_client.graphql(query)
    assert result["findMatchByID"]["_id"]
