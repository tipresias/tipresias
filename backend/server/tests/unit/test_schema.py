from django.test import TestCase
from graphene.test import Client

from server.schema import schema
from server.tests.fixtures.factories import FullMatchFactory
from server.models import Match
from server.tests.fixtures.factories import MLModelFactory

ROUND_COUNT = 2
YEAR_RANGE = (2014, 2016)
MODEL_NAMES = ["predictanator", "accurate_af"]


class TestSchema(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = Client(schema)

        ml_models = [MLModelFactory(name=model_name) for model_name in MODEL_NAMES]

        self.matches = [
            FullMatchFactory(
                year=year,
                prediction__ml_model=ml_models[0],
                prediction_two__ml_model=ml_models[1],
            )
            for year in range(*YEAR_RANGE)
            for _ in range(ROUND_COUNT)
        ]

    def test_predictions(self):
        expected_predictions = [
            {
                "match": {
                    "roundNumber": match.round_number,
                    "year": match.start_date_time.year,
                },
                "mlModel": {"name": prediction.ml_model.name},
                "isCorrect": prediction.is_correct,
            }
            for match in self.matches
            for prediction in match.prediction_set.all()
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

        self._assert_correct_prediction_results(
            executed["data"]["predictions"], expected_predictions
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
                pred for pred in expected_predictions if pred["match"]["year"] == 2015
            ]

            self._assert_correct_prediction_results(
                executed["data"]["predictions"], expected_predictions
            )

    def test_prediction_years(self):
        expected_years = list({match.start_date_time.year for match in self.matches})

        executed = self.client.execute(
            """
            query QueryType { predictionYears }
            """
        )

        self.assertEqual(expected_years, executed["data"]["predictionYears"])

    def test_cumulative_predictions(self):
        ml_model_names = (
            Match.objects.filter(start_date_time__year=2015)
            .distinct("prediction__ml_model__name")
            .values_list("prediction__ml_model__name", flat=True)
        )

        executed = self.client.execute(
            """
            query QueryType {
                yearlyPredictions(year: 2015) {
                    predictionModelNames
                    predictionsByRound {
                        roundNumber
                        modelPredictions { modelName, cumulativeCorrectCount }
                    }
                }
            }
            """
        )

        data = executed["data"]["yearlyPredictions"]

        self.assertEqual(set(data["predictionModelNames"]), set(ml_model_names))

        predictions = data["predictionsByRound"]

        earlier_round = predictions[0]
        later_round = predictions[1]

        self.assertLessEqual(earlier_round["roundNumber"], later_round["roundNumber"])

        earlier_round_counts = [
            prediction["cumulativeCorrectCount"]
            for prediction in earlier_round["modelPredictions"]
        ]
        later_round_counts = [
            prediction["cumulativeCorrectCount"]
            for prediction in later_round["modelPredictions"]
        ]

        self.assertLessEqual(sum(earlier_round_counts), sum(later_round_counts))

    def test_latest_round_predictions(self):
        executed = self.client.execute(
            """
            query QueryType {
                latestRoundPredictions(mlModelName: "accurate_af") {
                    roundNumber
                    matches {
                        predictionSet { predictedWinner { name }, predictedMargin }
                        teammatchSet { team { name } }
                    }
                }
            }
            """
        )

        data = executed["data"]["latestRoundPredictions"]
        max_match_round = max([match.round_number for match in self.matches])

        self.assertEqual(data["roundNumber"], max_match_round)

    def _assert_correct_prediction_results(self, results, expected_results):
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(results):
            expected_result = expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])
