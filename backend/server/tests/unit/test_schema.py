from datetime import date
import itertools
from dateutil import parser

from django.test import TestCase
from graphene.test import Client
import numpy as np

from server.schema import schema
from server.tests.fixtures.factories import FullMatchFactory
from server.models import Match, MLModel
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

    def test_fetch_predictions(self):
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
                fetchPredictions {
                    match { roundNumber, year },
                    mlModel { name },
                    isCorrect
                }
            }
            """
        )

        self._assert_correct_prediction_results(
            executed["data"]["fetchPredictions"], expected_predictions
        )

        with self.subTest("when year is 2015"):
            executed = self.client.execute(
                """
                query QueryType {
                    fetchPredictions(year: 2015) {
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
                executed["data"]["fetchPredictions"], expected_predictions
            )

    def test_fetch_prediction_years(self):
        expected_years = list({match.start_date_time.year for match in self.matches})

        executed = self.client.execute(
            """
            query QueryType { fetchPredictionYears }
            """
        )

        self.assertEqual(expected_years, executed["data"]["fetchPredictionYears"])

    def test_fetch_yearly_predictions(self):
        year = 2015
        ml_model_names = (
            Match.objects.filter(start_date_time__year=year)
            .distinct("prediction__ml_model__name")
            .values_list("prediction__ml_model__name", flat=True)
        )

        ml_models = list(MLModel.objects.filter(name__in=ml_model_names))

        # Have to make sure at least one match has a different round_number to compare
        # later rounds to earlier ones
        FullMatchFactory(
            year=year,
            round_number=50,
            prediction__ml_model=ml_models[0],
            prediction_two__ml_model=ml_models[1],
        )

        executed = self.client.execute(
            """
            query QueryType {
                fetchYearlyPredictions(year: 2015) {
                    seasonYear
                    predictionModelNames
                    predictionsByRound {
                        roundNumber
                        modelPredictions { modelName, cumulativeCorrectCount }
                        matches { predictions { isCorrect } }
                    }
                }
            }
            """
        )

        data = executed["data"]["fetchYearlyPredictions"]

        self.assertEqual(set(data["predictionModelNames"]), set(ml_model_names))
        self.assertEqual(data["seasonYear"], 2015)

        predictions = data["predictionsByRound"]

        earlier_round = predictions[0]
        later_round = predictions[1]

        self.assertLessEqual(earlier_round["roundNumber"], later_round["roundNumber"])

        earlier_round_cum_counts = [
            prediction["cumulativeCorrectCount"]
            for prediction in earlier_round["modelPredictions"]
        ]
        earlier_round_correct = [
            prediction["isCorrect"]
            for match in earlier_round["matches"]
            for prediction in match["predictions"]
        ]

        # Regression test to make sure cumulative counts are being calculated correctly
        self.assertEqual(sum(earlier_round_cum_counts), sum(earlier_round_correct))

        later_round_cum_counts = [
            prediction["cumulativeCorrectCount"]
            for prediction in later_round["modelPredictions"]
        ]
        later_round_correct = [
            prediction["isCorrect"]
            for match in later_round["matches"]
            for prediction in match["predictions"]
        ]

        # Regression test to make sure cumulative counts are being calculated correctly
        self.assertEqual(
            sum(earlier_round_correct + later_round_correct),
            sum(later_round_cum_counts),
        )

        self.assertLessEqual(sum(earlier_round_cum_counts), sum(later_round_cum_counts))

    def test_fetch_latest_round_predictions(self):
        ml_models = list(MLModel.objects.all())
        year = date.today().year

        latest_matches = [
            FullMatchFactory(
                year=year,
                prediction__ml_model=ml_models[0],
                prediction_two__ml_model=ml_models[1],
            )
            for _ in range(ROUND_COUNT)
        ]

        executed = self.client.execute(
            """
            query QueryType {
                fetchLatestRoundPredictions {
                    roundNumber
                    matches {
                        startDateTime
                        predictions { predictedWinner { name } predictedMargin }
                        winner { name }
                        homeTeam { name }
                        awayTeam { name }
                    }
                }
            }
            """
        )

        data = executed["data"]["fetchLatestRoundPredictions"]
        max_match_round = max([match.round_number for match in latest_matches])

        self.assertEqual(data["roundNumber"], max_match_round)

        match_years = [
            parser.parse(match["startDateTime"]).year for match in data["matches"]
        ]

        self.assertEqual(np.mean(match_years), year)

        with self.subTest("with an mlModelName argument"):
            executed_ml_name = self.client.execute(
                """
                query QueryType {
                    fetchLatestRoundPredictions {
                        roundNumber
                        matches {
                            startDateTime
                            predictions(mlModelName: "accurate_af") {
                                mlModel { name }
                            }
                        }
                    }
                }
                """
            )

            data = executed_ml_name["data"]["fetchLatestRoundPredictions"]
            predictions = itertools.chain.from_iterable(
                [match["predictions"] for match in data["matches"]]
            )
            ml_model_names = [pred["mlModel"]["name"] for pred in predictions]

            self.assertEqual(ml_model_names, ["accurate_af"])

    def _assert_correct_prediction_results(self, results, expected_results):
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(results):
            expected_result = expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])
