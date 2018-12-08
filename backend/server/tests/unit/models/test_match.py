import os
import sys
from datetime import datetime
from django.test import TestCase
from django.utils import timezone

from server.models import Match, Team, TeamMatch


class TestMatch(TestCase):
    def setUp(self):
        match_datetime = timezone.make_aware(datetime(2018, 5, 5))
        self.match = Match(start_date_time=match_datetime,
                           round_number=5)

    def test_year(self):
        self.assertEqual(self.match.year, 2018)

    def test_winner(self):
        self.match.save()
        home_team = Team(name='Richmond')
        home_team.save()
        away_team = Team(name='Melbourne')
        away_team.save()
        (TeamMatch(team=home_team, match=self.match, at_home=True, score=50)
         .save())
        (TeamMatch(team=away_team, match=self.match, at_home=False, score=100)
         .save())

        self.assertEqual(self.match.winner, away_team)
