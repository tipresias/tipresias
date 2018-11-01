import os
import sys
from unittest import TestCase
from faker import Faker
from django.core.exceptions import ValidationError

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../../')
)

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.models import Team

FAKE = Faker()


class TestTeam(TestCase):
    def setUp(self):
        self.team = Team(name='Richmond')

    def test_validation(self):
        with self.subTest(team=self.team):
            team = self.team
            team.full_clean()

        with self.subTest(team=Team(name='Bob')):
            team = Team(name='Bob')

            with self.assertRaises(ValidationError):
                team.full_clean()
