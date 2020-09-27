# pylint: disable=missing-docstring

from typing import List, Tuple

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.conf import settings
import numpy as np

from server.models import Team
from server.models.team import TeamCollection


def _create_random_teams() -> Tuple[int, List[str]]:
    team_count = np.random.randint(1, len(settings.TEAM_NAMES))
    team_names = np.random.permutation(settings.TEAM_NAMES)

    for n in range(team_count):
        Team.create(name=team_names[n])

    return team_count, team_names


class TestTeam(TestCase):
    def setUp(self):
        self.team = Team(name="Richmond")

    def test_validation(self):
        with self.subTest("with a valid team"):
            self.assertIsNone(self.team.full_clean())

        with self.subTest("with unrecognized team name"):
            team = Team(name="Bob")

            with self.assertRaises(ValidationError):
                team.full_clean()

        with self.subTest("with duplicate team name"):
            Team.create(name="Richmond")

            with self.assertRaises(ValidationError):
                self.team.full_clean()

    def test_count(self):
        team_count, _ = _create_random_teams()

        # It returns number of teams in DB
        self.assertEqual(Team.count(), team_count)

    def test_create(self):
        self.assertEqual(Team.count(), 0)

        team_name = np.random.choice(settings.TEAM_NAMES)
        team = Team.create(name=team_name)

        # It creates a DB record
        self.assertEqual(Team.count(), 1)
        # It returns the create team
        self.assertIsInstance(team, Team)
        self.assertEqual(team.name, team_name)

    def test_get(self):
        team_count, team_names = _create_random_teams()

        team_name = team_names[np.random.randint(0, team_count)]
        team = Team.get(name=team_name)

        # It returns the requested team
        self.assertIsInstance(team, Team)
        self.assertEqual(team.name, team_name)

    def test_all(self):
        team_count, _ = _create_random_teams()

        teams = Team.all()

        # It returns all teams
        self.assertEqual(len(teams), team_count)

    def test_get_or_create(self):
        with self.subTest("when it doesn't exist yet"):
            self.assertEqual(Team.count(), 0)
            team_name = np.random.choice(settings.TEAM_NAMES)
            team, was_created = Team.get_or_create(name=team_name)

            # It creates the team
            self.assertEqual(Team.count(), 1)
            # It returns the team record
            self.assertIsInstance(team, Team)
            self.assertEqual(team.name, team_name)
            # It returns that the team was created
            self.assertTrue(was_created)

        with self.subTest("when it already exists"):
            team, was_created = Team.get_or_create(name=team_name)

            # It doesn't create a new team
            self.assertEqual(Team.count(), 1)
            # It returns the team record
            self.assertIsInstance(team, Team)
            self.assertEqual(team.name, team_name)
            # It returns that the team wasn't created
            self.assertFalse(was_created)


class TestTeamCollection(TestCase):
    def setUp(self):
        _create_random_teams()

        self.team_collection = TeamCollection(Team.all())

    def test_delete(self):
        self.assertGreater(Team.count(), 0)
        self.team_collection.delete()

        # It deletes the team records
        self.assertEqual(Team.count(), 0)
