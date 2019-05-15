from django.test import TestCase
from graphene.test import Client

from server.schema import schema
from server.tests.fixtures.factories import FullMatchFactory

ROUND_COUNT = 1
YEAR_RANGE = (2014, 2016)


class TestSchema(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = Client(schema)

        matches = [
            FullMatchFactory(year=year)
            for year in range(*YEAR_RANGE)
            for _ in range(ROUND_COUNT)
        ]

        self.expected_predictions = [
            {
                "match": {
                    "roundNumber": match.round_number,
                    "year": match.start_date_time.year,
                },
                "mlModel": {"name": match.prediction_set.first().ml_model.name},
                "isCorrect": match.prediction_set.first().is_correct,
            }
            for match in matches
        ]

    def test_predictions(self):
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

        self._assert_correct_results(
            executed["data"]["predictions"], self.expected_predictions
        )

        with self.subTest("when year is 2015"):
            executed = self.client.execute(
                """
                query QueryType {
                    predictions(year: 2015) {
                        match { roundNumber, year },
                        mlModel { name },
                        isCorrect
                    }
                }
                """
            )

            expected_predictions = [
                pred
                for pred in self.expected_predictions
                if pred["match"]["year"] == 2015
            ]

            self._assert_correct_results(
                executed["data"]["predictions"], expected_predictions
            )

    def _assert_correct_results(self, results, expected_results):
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(results):
            expected_result = expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])
