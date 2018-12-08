from datetime import datetime
from django.test import TestCase
from django.utils import timezone
from graphene.test import Client

from server.schema import schema
from server.models import Team, Match, TeamMatch, MLModel, Prediction


class TestSchema(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = Client(schema)

        home_team = Team(name="Richmond")
        home_team.save()
        away_team = Team(name="Melbourne")
        away_team.save()

        match_datetime = timezone.make_aware(datetime(2018, 5, 5))
        new_match = Match(start_date_time=match_datetime, round_number=5)
        new_match.save()
        match_datetime = timezone.make_aware(datetime(2014, 5, 5))
        old_match = Match(start_date_time=match_datetime, round_number=7)
        old_match.save()

        (TeamMatch(team=home_team, match=new_match, at_home=True, score=150).save())
        (TeamMatch(team=away_team, match=new_match, at_home=False, score=100).save())
        (TeamMatch(team=home_team, match=old_match, at_home=True, score=150).save())
        (TeamMatch(team=away_team, match=old_match, at_home=False, score=100).save())

        ml_model = MLModel(name="test_model")
        ml_model.save()

        new_prediction = Prediction(
            match=new_match,
            ml_model=ml_model,
            predicted_winner=home_team,
            predicted_margin=50,
        )
        new_prediction.save()
        old_prediction = Prediction(
            match=old_match,
            ml_model=ml_model,
            predicted_winner=away_team,
            predicted_margin=50,
        )
        old_prediction.save()

    def assert_correct_results(self, results, expected_results):
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(results):
            expected_result = expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])

    def test_predictions(self):
        expected_predictions = [
            {
                "match": {"roundNumber": 5, "year": 2018},
                "mlModel": {"name": "test_model"},
                "isCorrect": True,
            },
            {
                "match": {"roundNumber": 7, "year": 2014},
                "mlModel": {"name": "test_model"},
                "isCorrect": False,
            },
        ]

        executed = self.client.execute(
            """
            query QueryType {
                predictions {
                    match { roundNumber, year },
                    mlModel { name },
                    isCorrect
                }
            }
        """
        )

        self.assert_correct_results(
            executed["data"]["predictions"], expected_predictions
        )

        with self.subTest(year=2018):
            executed = self.client.execute(
                """
                query QueryType {
                    predictions(year: 2018) {
                        match { roundNumber, year },
                        mlModel { name },
                        isCorrect
                    }
                }
            """
            )

            self.assert_correct_results(
                executed["data"]["predictions"], expected_predictions[:1]
            )
