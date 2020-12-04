# pylint: disable=missing-docstring

from tests.fixtures.factories import TeamMatchFactory, TeamFactory, MatchFactory


def test_creating_valid_team_match(faunadb_client):
    team = TeamFactory.create()
    match = MatchFactory.create()
    team_match = TeamMatchFactory.build(team=team, match=match)
    saved_team_match = team_match.create()

    # It returns the saved match
    assert saved_team_match == team_match

    # It saves the match in the DB
    query = "query { findTeamMatchByID(id: %s) { _id } }" % (saved_team_match.id)
    result = faunadb_client.graphql(query)
    assert result["findTeamMatchByID"]["_id"]
