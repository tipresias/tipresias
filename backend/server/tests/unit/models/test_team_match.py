# pylint: disable=missing-docstring

from typing import Tuple, List

from django.test import TestCase
import numpy as np

from server.models import TeamMatch
from server.models.team_match import TeamMatchCollection
from server.tests.fixtures.factories import MatchFactory, TeamMatchFactory, TeamFactory
from server.tests.fixtures import data_factories

ARBITRARY_TEAM_MATCH_LIMIT = 20


def _create_random_team_matches(
    count: int = ARBITRARY_TEAM_MATCH_LIMIT,
) -> Tuple[int, List[str]]:
    team_match_count = np.random.randint(1, count)

    return team_match_count, [TeamMatchFactory() for _ in range(team_match_count)]


class TestTeamMatch(TestCase):
    def setUp(self):
        self.match = MatchFactory()
        self.team = TeamFactory()
        self.fixture_data = data_factories.fake_fixture_data().to_dict("records")

    def test_get_or_create_from_raw_data(self):
        self.assertEqual(TeamMatch.count(), 0)

        team_matches = TeamMatch.get_or_create_from_raw_data(
            self.match, self.fixture_data[0]
        )

        self.assertEqual(TeamMatch.count(), 2)

        for team_match in team_matches:
            self.assertIsInstance(team_match, TeamMatch)
            self.assertEqual(team_match.match, self.match)
            self.assertEqual(team_match.score, 0)

        with self.subTest("when associated team matches already exist"):
            existing_team_matches = TeamMatch.get_or_create_from_raw_data(
                self.match, self.fixture_data[0]
            )

            self.assertEqual(TeamMatch.count(), 2)
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
            match_data = data_factories.fake_match_results_data().to_dict("records")[0]

            home_team, away_team = TeamMatch.get_or_create_from_raw_data(
                new_match, match_data
            )

            self.assertEqual(home_team.score, match_data["home_score"])
            self.assertEqual(away_team.score, match_data["away_score"])

    def test_update_score(self):
        match_result = data_factories.fake_match_results_data().iloc[0, :]

        team_match = TeamMatchFactory(
            team__name=match_result["home_team"], at_home=True, score=0
        )

        team_match.update_score(match_result)

        self.assertEqual(team_match.score, match_result["home_score"])

    def test_count(self):
        team_match_count, _ = _create_random_team_matches()

        # It returns number of teams in DB
        self.assertEqual(TeamMatch.count(), team_match_count)

    def test_create(self):
        self.assertEqual(TeamMatch.count(), 0)

        team = TeamMatch.create(
            match=self.match, team=self.team, at_home=np.random.randint(0, 2)
        )

        # It creates a DB record
        self.assertEqual(TeamMatch.count(), 1)
        # It returns the create team match
        self.assertIsInstance(team, TeamMatch)
        self.assertEqual(team.match.id, self.match.id)

    def test_get(self):
        team_match_count, team_matches = _create_random_team_matches()
        random_team_match = team_matches[np.random.randint(0, team_match_count)]

        team_match = TeamMatch.get(
            match__start_date_time=random_team_match.match.start_date_time,
            team__name=random_team_match.team.name,
        )

        # It returns the requested team match
        self.assertIsInstance(team_match, TeamMatch)
        self.assertEqual(team_match.match.id, random_team_match.match.id)
        self.assertEqual(team_match.team.id, random_team_match.team.id)

    def test_all(self):
        team_match_count, _ = _create_random_team_matches()

        team_matches = TeamMatch.all()

        # It returns all team matches
        self.assertEqual(len(team_matches), team_match_count)

    def test_filter(self):
        _, team_matches = _create_random_team_matches(count=100)
        team_names = np.array([team_match.team.name for team_match in team_matches])
        unique_team_names, team_name_counts = np.unique(team_names, return_counts=True)

        index = np.random.randint(len(unique_team_names))
        record_count = team_name_counts[index]
        team_name = unique_team_names[index]

        team_matches = TeamMatch.filter(team__name=team_name)

        # It returns filtered team matches
        self.assertEqual(len(team_matches), record_count)
        self.assertTrue(
            all([team_match.team.name == team_name for team_match in team_matches])
        )

    def test_get_or_create(self):
        at_home = np.random.randint(0, 2)

        with self.subTest("when it doesn't exist yet"):
            self.assertEqual(TeamMatch.count(), 0)
            team_match, was_created = TeamMatch.get_or_create(
                match=self.match, team=self.team, at_home=at_home
            )

            # It creates the team match
            self.assertEqual(TeamMatch.count(), 1)
            # It returns the team match record
            self.assertIsInstance(team_match, TeamMatch)
            self.assertEqual(team_match.match.id, self.match.id)
            self.assertEqual(team_match.team.id, self.team.id)
            # It returns that the team match was created
            self.assertTrue(was_created)

        with self.subTest("when it already exists"):
            team_match, was_created = TeamMatch.get_or_create(
                match=self.match, team=self.team, at_home=at_home
            )

            # It doesn't create a new team match
            self.assertEqual(TeamMatch.count(), 1)
            # It returns the team match record
            self.assertIsInstance(team_match, TeamMatch)
            self.assertEqual(team_match.match.id, self.match.id)
            self.assertEqual(team_match.team.id, self.team.id)
            # It returns that the team match wasn't created
            self.assertFalse(was_created)


class TestTeamMatchCollection(TestCase):
    def setUp(self):
        _create_random_team_matches()

        self.team_match_collection = TeamMatchCollection(TeamMatch.all())

    def test_delete(self):
        self.assertGreater(TeamMatch.count(), 0)
        self.team_match_collection.delete()

        # It deletes the team records
        self.assertEqual(TeamMatch.count(), 0)

    def test_count(self):
        self.assertEqual(self.team_match_collection.count(), TeamMatch.count())

    def test_order_by(self):
        sorted_team_scores = np.sort(
            [team_match.score for team_match in self.team_match_collection]
        )
        sorted_team_matches = self.team_match_collection.order_by("score")

        scores_are_sorted = np.all(
            sorted_team_scores
            == np.array([team_match.score for team_match in sorted_team_matches])
        )

        self.assertTrue(scores_are_sorted)

    def test_update(self):
        team_match_scores = [
            team_match.score for team_match in self.team_match_collection
        ]
        unique_team_match_scores = np.unique(team_match_scores)

        # Not all team names are the same
        self.assertNotEqual(len(unique_team_match_scores), 1)

        n_updated_team_matches = self.team_match_collection.update(
            score=team_match_scores[np.random.randint(len(team_match_scores) - 1)]
        )

        # It returns count of updated records
        self.assertEqual(n_updated_team_matches, len(self.team_match_collection))

        unique_updated_team_match_scores = np.unique(
            [team_match.score for team_match in self.team_match_collection]
        )

        # It updates the given attribute for all team matches in the collection
        self.assertEqual(len(unique_updated_team_match_scores), 1)
