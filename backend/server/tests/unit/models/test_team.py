from django.test import TestCase
from django.core.exceptions import ValidationError

from server.models import Team


class TestTeam(TestCase):
    def setUp(self):
        self.team = Team(name="Richmond")

    def test_validation(self):
        with self.subTest(team=self.team):
            team = self.team
            team.full_clean()

        with self.subTest(team=Team(name="Bob")):
            team = Team(name="Bob")

            with self.assertRaises(ValidationError):
                team.full_clean()

        with self.subTest(team=self.team):
            team = Team(name="Richmond")
            Team(name="Richmond").save()

            with self.assertRaises(ValidationError):
                team.full_clean()
