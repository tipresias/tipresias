from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from server.models import Match, Team


class TestMatch(TestCase):
    def setUp(self):
        match_datetime = timezone.make_aware(datetime(2018, 5, 5))
        self.match = Match.objects.create(
            start_date_time=match_datetime, round_number=5, venue="Corporate Stadium"
        )
        self.home_team = Team.objects.create(name="Richmond")
        self.away_team = Team.objects.create(name="Melbourne")

        self.match.teammatch_set.create(
            team=self.home_team, match=self.match, at_home=True, score=50
        )
        self.match.teammatch_set.create(
            team=self.away_team, match=self.match, at_home=False, score=100
        )

    def test_year(self):
        self.assertEqual(self.match.year, 2018)

    def test_winner(self):
        self.assertEqual(self.match.winner, self.away_team)

    def test_is_draw(self):
        self.assertFalse(self.match.is_draw)

        self.match.teammatch_set.update(score=100)
        self.assertTrue(self.match.is_draw)

    def test_has_been_played(self):
        self.assertTrue(self.match.has_been_played)

        with self.subTest("when there's no score"):
            self.match.teammatch_set.update(score=0)

            self.assertFalse(self.match.has_been_played)

        with self.subTest("when the match hasn't finished yet"):
            team_match = self.match.teammatch_set.first()
            team_match.score = 100
            team_match.save()

            self.match.start_date_time = datetime.now(timezone.utc) - timedelta(hours=1)
            self.match.save()

            self.assertFalse(self.match.has_been_played)

    def test_validations(self):
        invalid_match = Match(
            start_date_time=self.match.start_date_time,
            venue=self.match.venue,
            round_number=2,
        )

        with self.assertRaises(ValidationError):
            invalid_match.full_clean()
