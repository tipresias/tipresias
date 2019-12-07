from copy import copy

from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.db.utils import DataError
from django.core.exceptions import ValidationError

from server.models import Match, Team
from server.tests.fixtures.data_factories import fake_fixture_data


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

    def test_get_or_create_from_raw_data(self):
        fixture_data = fake_fixture_data(1, (2015, 2016)).to_dict("records")[0]
        match_count = Match.objects.count()

        with self.subTest("with validation error"):
            invalid_fixture_data = copy(fixture_data)
            invalid_fixture_data["venue"] = "venue" * 25

            with self.assertRaises(DataError):
                Match.get_or_create_from_raw_data(invalid_fixture_data)

            self.assertEqual(Match.objects.count(), match_count)

        created_match = Match.get_or_create_from_raw_data(fixture_data)

        self.assertIsInstance(created_match, Match)
        self.assertEqual(Match.objects.count(), match_count + 1)

        with self.subTest("with existing match record"):
            gotten_match = Match.get_or_create_from_raw_data(fixture_data)

            self.assertEqual(gotten_match, created_match)
            self.assertEqual(Match.objects.count(), match_count + 1)

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

            self.match.start_date_time = timezone.localtime() - timedelta(hours=1)
            self.match.save()

            self.assertFalse(self.match.has_been_played)

    def test_validations(self):
        self.match.full_clean()

        with self.subTest("with duplicate start_date_time/venue combination"):
            invalid_match = Match(
                start_date_time=self.match.start_date_time,
                venue=self.match.venue,
                round_number=2,
            )

            with self.assertRaises(ValidationError, msg="duplicate"):
                invalid_match.full_clean()

        with self.subTest("with a timezone-unaware start_date_time"):
            invalid_start_date_time = datetime.now()
            invalid_match = Match(
                start_date_time=invalid_start_date_time,
                venue="Some Venue",
                round_number=5,
            )

            with self.assertRaises(
                ValidationError, msg=f"{invalid_start_date_time} is not set to the UTC"
            ):
                invalid_match.full_clean()
