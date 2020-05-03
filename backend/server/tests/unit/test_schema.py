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
from server.models import Match, MLModel, Prediction
from server.models.ml_model import PredictionType


ROUND_COUNT = 4
MATCH_COUNT = 3
YEAR_RANGE = (2014, 2016)
MODEL_NAMES = ["predictanator", "accurate_af"]
TWENTY_SEVENTEEN = 2017


class TestSchema(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = Client(schema)

        self.ml_models = [
            MLModelFactory(
                name=model_name,
                is_principle=(idx == 0),
                used_in_competitions=True,
                prediction_type=PredictionType.values[idx],
            )
            for idx, model_name in enumerate(MODEL_NAMES)
        ]

        self.matches = [
            FullMatchFactory(
                year=year,
                round_number=((round_n % 23) + 1),
                start_date_time=timezone.make_aware(
                    datetime(year, 6, (round_n % 29) + 1, match_n * 5)
                ),
                prediction__ml_model=self.ml_models[0],
                prediction_two__ml_model=self.ml_models[1],
            )
            for year in range(*YEAR_RANGE)
            for round_n in range(ROUND_COUNT)
            for match_n in range(MATCH_COUNT)
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

    def test_fetch_season_performance_chart_parameters(self):
        expected_years = list({match.start_date_time.year for match in self.matches})

        executed = self.client.execute(
            """
            query QueryType {
                fetchSeasonPerformanceChartParameters {
                    availableSeasons
                    availableMlModels {
                        name
                    }
                }
            }
            """
        )

        data = executed["data"]["fetchSeasonPerformanceChartParameters"]

        self.assertEqual(expected_years, data["availableSeasons"])

        db_ml_model_names = [model.name for model in self.ml_models]
        query_ml_model_names = [model["name"] for model in data["availableMlModels"]]
        self.assertEqual(sorted(db_ml_model_names), sorted(query_ml_model_names))

        with self.subTest("with an MLModel without any predictions"):
            predictionless_ml_model = MLModel(name="no_predictions")
            predictionless_ml_model.save()

            data = executed["data"]["fetchSeasonPerformanceChartParameters"]

            query_ml_model_names = [
                model["name"] for model in data["availableMlModels"]
            ]
            self.assertNotIn(predictionless_ml_model.name, query_ml_model_names)

    def test_fetch_season_model_metrics(self):
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
            query($season: Int) {
                fetchSeasonModelMetrics(season: $season) {
                    season
                    roundModelMetrics {
                        roundNumber
                        modelMetrics {
                            mlModel { name }
                            cumulativeCorrectCount
                            cumulativeAccuracy
                            cumulativeMeanAbsoluteError
                            cumulativeMarginDifference
                            cumulativeBits
                        }
                    }
                }
            }
            """,
            variables={"season": year},
        )

        data = executed["data"]["fetchSeasonModelMetrics"]

        self.assertEqual(data["season"], year)

        predictions = data["roundModelMetrics"]

        for pred in predictions:
            for model_metric in pred["modelMetrics"]:
                self.assertGreaterEqual(model_metric["cumulativeAccuracy"], 0.0)
                self.assertLessEqual(model_metric["cumulativeAccuracy"], 1.0)

        earlier_round = predictions[0]
        later_round = predictions[1]

        self.assertLess(earlier_round["roundNumber"], later_round["roundNumber"])

        earlier_round_cum_correct = [
            prediction["cumulativeCorrectCount"]
            for prediction in earlier_round["modelMetrics"]
        ]
        earlier_round_cum_accuracy = [
            prediction["cumulativeAccuracy"]
            for prediction in earlier_round["modelMetrics"]
        ]

        earlier_round_correct = Prediction.objects.filter(
            match__start_date_time__year=year,
            match__round_number=earlier_round["roundNumber"],
        ).values_list("is_correct", flat=True)

        # Regression tests to make sure cumulative counts and cumulative accuracy
        # are being calculated correctly
        self.assertEqual(sum(earlier_round_cum_correct), sum(earlier_round_correct))
        self.assertEqual(
            sum(earlier_round_cum_accuracy) / len(earlier_round_cum_accuracy),
            sum(earlier_round_correct) / len(earlier_round_correct),
        )

        later_round_cum_correct = [
            prediction["cumulativeCorrectCount"]
            for prediction in later_round["modelMetrics"]
        ]
        later_round_correct = Prediction.objects.filter(
            match__start_date_time__year=year,
            match__round_number=later_round["roundNumber"],
        ).values_list("is_correct", flat=True)

        # Regression test to make sure cumulative counts are being calculated correctly
        self.assertEqual(
            sum(earlier_round_correct) + sum(later_round_correct),
            sum(later_round_cum_correct),
        )

        self.assertLessEqual(
            sum(earlier_round_cum_correct), sum(later_round_cum_correct)
        )

        with self.subTest("with mlModelName argument 'predictanator'"):
            executed = self.client.execute(
                """
                query QueryType {
                    fetchSeasonModelMetrics(season: 2015) {
                        roundModelMetrics {
                            modelMetrics(mlModelName: "predictanator") {
                                mlModel { name }
                            }
                        }
                    }
                }
                """
            )

            data = executed["data"]["fetchSeasonModelMetrics"]["roundModelMetrics"][0]

            self.assertEqual(len(data["modelMetrics"]), 1)
            self.assertEqual(
                data["modelMetrics"][0]["mlModel"]["name"], "predictanator"
            )

        with self.subTest("with roundNumber argument of -1"):
            executed = self.client.execute(
                """
                query QueryType {
                    fetchSeasonModelMetrics(season: 2015) {
                        roundModelMetrics(roundNumber: -1) { roundNumber }
                    }
                }
                """
            )

            data = executed["data"]["fetchSeasonModelMetrics"]["roundModelMetrics"]

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
                round_number=((round_n % 23) + 1),
                start_date_time=timezone.make_aware(
                    datetime(year, 6, (round_n % 29) + 1)
                ),
                prediction__ml_model=ml_models[0],
                prediction_two__ml_model=ml_models[1],
            )
            for round_n in range(ROUND_COUNT)
        ]

        executed = self.client.execute(
            """
            query QueryType {
                fetchLatestRoundPredictions {
                    roundNumber
                    matchPredictions {
                        startDateTime
                        predictedWinner
                        predictedMargin
                        predictedWinProbability
                        isCorrect
                    }
                }
            }
            """
        )

        data = executed["data"]["fetchLatestRoundPredictions"]

        max_match_round = max([match.round_number for match in latest_matches])
        self.assertEqual(data["roundNumber"], max_match_round)

        match_years = [
            parser.parse(pred["startDateTime"]).year
            for pred in data["matchPredictions"]
        ]
        self.assertEqual(np.mean(match_years), year)

        principle_predicted_winners = Prediction.objects.filter(
            match__start_date_time__year=year,
            match__round_number=max_match_round,
            ml_model__is_principle=True,
        ).values_list("predicted_winner__name", flat=True)
        query_predicted_winners = [
            pred["predictedWinner"] for pred in data["matchPredictions"]
        ]
        self.assertEqual(
            sorted(principle_predicted_winners), sorted(query_predicted_winners)
        )

    # Keeping this in a separate test, because it requires special setup
    # to properly test metric calculations
    def test_fetch_season_model_metrics_cumulative_metrics(self):
        ml_models = list(MLModel.objects.filter(name__in=MODEL_NAMES))
        YEAR = TWENTY_SEVENTEEN
        MONTH = 6

        for round_n in range(ROUND_COUNT):
            for match_n in range(MATCH_COUNT):
                FullMatchFactory(
                    year=YEAR,
                    round_number=(round_n + 1),
                    start_date_time=timezone.make_aware(
                        datetime(YEAR, MONTH, (round_n % 29) + 1, match_n * 5)
                    ),
                    prediction__ml_model=ml_models[0],
                    prediction__force_correct=True,
                    prediction_two__ml_model=ml_models[1],
                    prediction_two__force_correct=True,
                )

        query = """
            query($mlModelName: String) {
                fetchSeasonModelMetrics(season: 2017) {
                    season
                    roundModelMetrics(roundNumber: -1) {
                        roundNumber
                        modelMetrics(mlModelName: $mlModelName) {
                            mlModel { name }
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

        with self.subTest("for a 'Margin' model"):
            executed = self.client.execute(
                query, variables={"mlModelName": "accurate_af"}
            )

            data = executed["data"]["fetchSeasonModelMetrics"]["roundModelMetrics"][0][
                "modelMetrics"
            ]

            self.assertEqual(len(data), 1)
            model_stats = data[0]
            self.assertEqual("accurate_af", model_stats["mlModel"]["name"])

            self.assertGreater(model_stats["cumulativeCorrectCount"], 0)
            self.assertEqual(model_stats["cumulativeMeanAbsoluteError"], 0)
            self.assertEqual(model_stats["cumulativeMarginDifference"], 0)
            self.assertGreater(model_stats["cumulativeAccuracy"], 0)
            # Bits can be positive or negative, so we just want to make sure it's not 0,
            # which would suggest a problem
            self.assertNotEqual(model_stats["cumulativeBits"], 0)

        with self.subTest("for a 'Win Probability' model"):
            executed = self.client.execute(
                query, variables={"mlModelName": "predictanator"}
            )

            data = executed["data"]["fetchSeasonModelMetrics"]["roundModelMetrics"][0][
                "modelMetrics"
            ]

            self.assertEqual(len(data), 1)
            model_stats = data[0]
            self.assertEqual("predictanator", model_stats["mlModel"]["name"])

            self.assertGreater(model_stats["cumulativeCorrectCount"], 0)
            self.assertGreater(model_stats["cumulativeMeanAbsoluteError"], 0)
            self.assertGreater(model_stats["cumulativeMarginDifference"], 0)
            self.assertGreater(model_stats["cumulativeAccuracy"], 0)
            self.assertEqual(model_stats["cumulativeBits"], 0)

        with self.subTest("when the last matches haven't been played yet"):
            DAY = 3
            fake_datetime = timezone.make_aware(datetime(YEAR, MONTH, DAY))

            with freeze_time(fake_datetime):
                past_executed = self.client.execute(
                    query, variables={"mlModelName": "predictanator"}
                )

                data = past_executed["data"]["fetchSeasonModelMetrics"][
                    "roundModelMetrics"
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

    def test_fetch_ml_models(self):
        N_MODELS = 3

        for _ in range(N_MODELS):
            MLModelFactory()

        query = """
            query QueryType {
                fetchMlModels {
                    name
                    usedInCompetitions
                }
            }
        """

        data = self.client.execute(query)["data"]["fetchMlModels"]
        self.assertEqual(len(data), N_MODELS + len(MODEL_NAMES))

        with self.subTest("when forCompetitionsOnly is true"):
            for _ in range(4):
                MLModelFactory()

            query = """
                query QueryType {
                    fetchMlModels(forCompetitionOnly: true) {
                        name
                        usedInCompetitions
                        isPrinciple
                    }
                }
            """

            data = self.client.execute(query)["data"]["fetchMlModels"]

            self.assertEqual(len(data), len(MODEL_NAMES))
            self.assertLess(len(data), MLModel.objects.count())

            for model in data:
                self.assertTrue(model["usedInCompetitions"])

    def _assert_correct_prediction_results(self, results, expected_results):
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(results):
            expected_result = expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])
