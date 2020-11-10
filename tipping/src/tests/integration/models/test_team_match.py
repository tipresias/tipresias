# pylint: disable=missing-docstring

from tests.fixtures.factories import TeamFactory, MatchFactory, TeamMatchFactory


def test_saving_valid_team(faunadb_client):
    team = TeamFactory.create()
    match = MatchFactory.create(winner=team)

    team_match = TeamMatchFactory.build(team=team, match=match)
    saved_team_match = team_match.create()

    # It returns the saved team-match
    assert saved_team_match == team_match

    # It saves the team-match in the DB
    query = f"query {{ findTeamMatchByID(id: {saved_team_match.id}) {{ _id }} }}"
    result = faunadb_client.graphql(query)
    assert result["findTeamMatchByID"]["_id"]
