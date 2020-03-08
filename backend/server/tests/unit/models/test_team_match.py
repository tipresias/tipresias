# pylint: disable=missing-docstring
from django.test import TestCase

from server.models import TeamMatch
from server.tests.fixtures.factories import MatchFactory, TeamMatchFactory
from server.tests.fixtures.data_factories import (
    fake_fixture_data,
    fake_match_results_data,
)


class TestTeamMatch(TestCase):
    def setUp(self):
        self.match = MatchFactory()
        self.fixture_data = fake_fixture_data(2, (2015, 2016)).to_dict("records")

    def test_get_or_create_from_raw_data(self):
        self.assertEqual(TeamMatch.objects.count(), 0)

        team_matches = TeamMatch.get_or_create_from_raw_data(
            self.match, self.fixture_data[0]
        )

        self.assertEqual(TeamMatch.objects.count(), 2)

        for team_match in team_matches:
            self.assertIsInstance(team_match, TeamMatch)
            self.assertEqual(team_match.match, self.match)
            self.assertEqual(team_match.score, 0)

        with self.subTest("when associated team matches already exist"):
            existing_team_matches = TeamMatch.get_or_create_from_raw_data(
                self.match, self.fixture_data[0]
            )

            self.assertEqual(TeamMatch.objects.count(), 2)
            self.assertEqual(team_matches, existing_team_matches)

            with self.subTest("but teams in match data are different"):
                with self.assertRaisesRegex(
                    AssertionError, r"Team names in the teammatch_set"
                ):
                    TeamMatch.get_or_create_from_raw_data(
                        self.match, self.fixture_data[1]
                    )

        with self.subTest("when the raw data has match results"):
            new_match = MatchFactory()
            match_data = fake_match_results_data(1, (2016, 2017)).to_dict("records")[0]

            home_team, away_team = TeamMatch.get_or_create_from_raw_data(
                new_match, match_data
            )

            self.assertEqual(home_team.score, match_data["home_score"])
            self.assertEqual(away_team.score, match_data["away_score"])

    def test_update_score(self):
        match_result = fake_match_results_data(1, (2014, 2015)).iloc[0, :]

        team_match = TeamMatchFactory(
            team__name=match_result["home_team"], at_home=True, score=0
        )

        team_match.update_score(match_result)

        self.assertEqual(team_match.score, match_result["home_score"])
