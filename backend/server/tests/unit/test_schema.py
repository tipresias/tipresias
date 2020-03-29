# pylint: disable=missing-docstring
from datetime import datetime
import itertools
from dateutil import parser

from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
import numpy as np
from freezegun import freeze_time

from server.graphql import schema
from server.tests.fixtures.factories import FullMatchFactory, MLModelFactory
from server.models import Match, MLModel


ROUND_COUNT = 4
YEAR_RANGE = (2014, 2016)
MODEL_NAMES = ["predictanator", "accurate_af"]
TWENTY_SEVENTEEN = 2017


class TestSchema(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = Client(schema)

        ml_models = [MLModelFactory(name=model_name) for model_name in MODEL_NAMES]

        self.matches = [
            FullMatchFactory(
                year=year,
                round_number=((idx % 23) + 1),
                start_date_time=timezone.make_aware(datetime(year, 6, (idx % 29) + 1)),
                prediction__ml_model=ml_models[0],
                prediction_two__ml_model=ml_models[1],
            )
            for year in range(*YEAR_RANGE)
            for idx in range(ROUND_COUNT)
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
            start_date_time=timezone.make_aware(datetime(year, 10, 31)),
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
                        modelMetrics {
                            modelName
                            cumulativeCorrectCount
                            cumulativeAccuracy
                            cumulativeMeanAbsoluteError
                            cumulativeMarginDifference
                            cumulativeBits
                        }
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

        for pred in predictions:
            for model_metric in pred["modelMetrics"]:
                self.assertGreaterEqual(model_metric["cumulativeAccuracy"], 0.0)
                self.assertLessEqual(model_metric["cumulativeAccuracy"], 1.0)

        earlier_round = predictions[0]
        later_round = predictions[1]

        self.assertLessEqual(earlier_round["roundNumber"], later_round["roundNumber"])

        earlier_round_cum_counts = [
            prediction["cumulativeCorrectCount"]
            for prediction in earlier_round["modelMetrics"]
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
            for prediction in later_round["modelMetrics"]
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

        with self.subTest("with mlModelName argument 'predictanator'"):
            executed = self.client.execute(
                """
                query QueryType {
                    fetchYearlyPredictions(year: 2015) {
                        predictionsByRound {
                            modelMetrics(mlModelName: "predictanator") { modelName }
                            matches { predictions { isCorrect } }
                        }
                    }
                }
                """
            )

            data = executed["data"]["fetchYearlyPredictions"]["predictionsByRound"][0]

            self.assertEqual(len(data["modelMetrics"]), 1)
            self.assertEqual(data["modelMetrics"][0]["modelName"], "predictanator")
            # matches and predictions associations are unaffected
            # by the modelMetrics argument (predictions has its own argument
            # for mlModelName)
            self.assertEqual(len(data["matches"][0]["predictions"]), len(ml_models))

        with self.subTest("with roundNumber argument of -1"):
            executed = self.client.execute(
                """
                query QueryType {
                    fetchYearlyPredictions(year: 2015) {
                        predictionsByRound(roundNumber: -1) { roundNumber }
                    }
                }
                """
            )

            data = executed["data"]["fetchYearlyPredictions"]["predictionsByRound"]

            self.assertEqual(len(data), 1)
            self.assertEqual(
                data[0]["roundNumber"],
                Match.objects.order_by("round_number").last().round_number,
            )

    def test_fetch_latest_round_predictions(self):
        ml_models = list(MLModel.objects.all())
        year = TWENTY_SEVENTEEN

        latest_matches = [
            FullMatchFactory(
                year=year,
                round_number=((idx % 23) + 1),
                start_date_time=timezone.make_aware(datetime(year, 6, (idx % 29) + 1)),
                prediction__ml_model=ml_models[0],
                prediction_two__ml_model=ml_models[1],
            )
            for idx in range(ROUND_COUNT)
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

    # Keeping this in a separate test, because it requires special setup
    # to properly test metric calculations
    def test_fetch_yearly_predictions_cumulative_metrics(self):
        ml_models = list(MLModel.objects.all())
        YEAR = TWENTY_SEVENTEEN
        MONTH = 6

        for idx in range(ROUND_COUNT):
            FullMatchFactory(
                year=YEAR,
                round_number=(idx + 1),
                start_date_time=timezone.make_aware(
                    datetime(YEAR, MONTH, (idx % 29) + 1)
                ),
                prediction__ml_model=ml_models[0],
                prediction__force_correct=True,
                prediction_two__ml_model=ml_models[1],
                prediction_two__force_correct=True,
            )

        query = """
            query QueryType {
                fetchYearlyPredictions(year: 2017) {
                    seasonYear
                    predictionsByRound(roundNumber: -1) {
                        roundNumber
                        modelMetrics(mlModelName: "accurate_af") {
                            modelName
                            cumulativeCorrectCount
                            cumulativeMeanAbsoluteError
                            cumulativeMarginDifference
                            cumulativeAccuracy
                            cumulativeBits
                        }
                    }
                }
            }
            """

        executed = self.client.execute(query)

        data = executed["data"]["fetchYearlyPredictions"]["predictionsByRound"][0][
            "modelMetrics"
        ]

        self.assertEqual(len(data), 1)
        model_stats = data[0]
        self.assertEqual("accurate_af", model_stats["modelName"])

        self.assertGreater(model_stats["cumulativeCorrectCount"], 0)
        self.assertGreater(model_stats["cumulativeMeanAbsoluteError"], 0)
        self.assertGreater(model_stats["cumulativeMarginDifference"], 0)
        self.assertGreater(model_stats["cumulativeAccuracy"], 0)
        # Bits can be positive or negative, so we just want to make sure it's not 0,
        # which would suggest a problem
        self.assertNotEqual(model_stats["cumulativeBits"], 0)

        with self.subTest("when the last matches haven't been played yet"):
            DAY = 3
            fake_datetime = timezone.make_aware(datetime(YEAR, MONTH, DAY))

            with freeze_time(fake_datetime):
                past_executed = self.client.execute(query)

                data = past_executed["data"]["fetchYearlyPredictions"][
                    "predictionsByRound"
                ][0]

                max_match_round = (
                    Match.objects.all().order_by("-round_number").first().round_number
                )
                self.assertLess(data["roundNumber"], max_match_round)
                # Last played match will be from day before, because "now" and the
                # start time for "today's match" are equal
                self.assertEqual(data["roundNumber"], DAY - 1)

                model_stats = data["modelMetrics"][0]

                self.assertGreater(model_stats["cumulativeCorrectCount"], 0)
                self.assertGreater(model_stats["cumulativeMeanAbsoluteError"], 0)
                self.assertGreater(model_stats["cumulativeMarginDifference"], 0)

    def _assert_correct_prediction_results(self, results, expected_results):
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(results):
            expected_result = expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])
