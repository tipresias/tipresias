# pylint: disable=missing-docstring
from django.test import TestCase
from django.core.exceptions import ValidationError

from server.models import Team


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
            Team.objects.create(name="Richmond")

            with self.assertRaises(ValidationError):
                self.team.full_clean()
