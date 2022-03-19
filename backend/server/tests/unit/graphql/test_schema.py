# pylint: disable=missing-docstring

from datetime import datetime
from dateutil import parser

from django.test import TestCase
from django.utils import timezone
from graphene.test import Client
import numpy as np
from freezegun import freeze_time

from server.graphql import schema
from server.tests.fixtures.factories import FullMatchFactory, MLModelFactory
from server.models import Match, MLModel, Prediction, TeamMatch
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
                is_principal=(idx == 0),
                used_in_competitions=True,
                # pylint: disable=unsubscriptable-object
                prediction_type=PredictionType.values[idx],
            )
            for idx, model_name in enumerate(MODEL_NAMES)
        ]

        self.matches = [
            FullMatchFactory(
                with_predictions=True,
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
                        predictionSeasons
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

        for model in data["availableMlModels"]:
            prediction_seasons = (
                MLModel.objects.prefetch_related("prediction_set")
                .get(name=model["name"])
                .prediction_set.distinct("match__start_date_time__year")
                .values_list("match__start_date_time__year", flat=True)
            )
            self.assertEqual(set(model["predictionSeasons"]), set(prediction_seasons))

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
        match_round_number = 50
        match_start_date_time = timezone.make_aware(datetime(year, 10, 31))
        FullMatchFactory(
            with_predictions=True,
            year=year,
            round_number=match_round_number,
            start_date_time=match_start_date_time,
            prediction__ml_model=ml_models[0],
            prediction_two__ml_model=ml_models[1],
        )

        query = """
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
        """
        variables = {"season": year}
        executed = self.client.execute(query, variables=variables)

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
            round(sum(earlier_round_cum_accuracy) / len(earlier_round_cum_accuracy), 4),
            round(sum(earlier_round_correct) / len(earlier_round_correct), 4),
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

        with self.subTest("when no matches have been played yet this year"):
            unplayed_season = max(YEAR_RANGE)

            with freeze_time(timezone.make_aware(datetime(unplayed_season, 1, 2))):
                FullMatchFactory(
                    with_predictions=True,
                    year=unplayed_season,
                    prediction__ml_model=ml_models[0],
                    prediction_two__ml_model=ml_models[1],
                )

                executed = self.client.execute(
                    query, variables={"season": unplayed_season}
                )
                self.assertEqual(executed.get("errors"), None)

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

            max_round_number = max(
                Match.objects.all(), key=lambda match: match.round_number
            ).round_number
            self.assertEqual(data[0]["roundNumber"], max_round_number)

    def test_fetch_latest_round_predictions(self):
        ml_models = list(MLModel.objects.all())
        latest_year = TWENTY_SEVENTEEN

        latest_matches = [
            FullMatchFactory(
                with_predictions=True,
                year=latest_year,
                round_number=((round_n % 23) + 1),
                start_date_time=timezone.make_aware(
                    datetime(latest_year, 6, (round_n % 29) + 1)
                ),
                prediction__ml_model=ml_models[0],
                prediction__force_correct=True,
                prediction_two__ml_model=ml_models[1],
                prediction_two__force_incorrect=True,
            )
            for round_n in range(ROUND_COUNT)
        ]

        query_string = """
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

        executed = self.client.execute(query_string)
        data = executed["data"]["fetchLatestRoundPredictions"]

        # It returns predictions from the last available round
        max_match_round = max([match.round_number for match in latest_matches])
        self.assertEqual(data["roundNumber"], max_match_round)

        # It returns predictions from the last available season
        match_years = [
            parser.parse(pred["startDateTime"]).year
            for pred in data["matchPredictions"]
        ]
        self.assertEqual(np.mean(match_years), latest_year)

        # It uses predicted winners from the principal model only
        principal_predicted_winners = Prediction.objects.filter(
            match__start_date_time__year=latest_year,
            match__round_number=max_match_round,
            ml_model__is_principal=True,
        ).values_list("predicted_winner__name", flat=True)
        query_predicted_winners = [
            pred["predictedWinner"] for pred in data["matchPredictions"]
        ]
        self.assertEqual(
            sorted(principal_predicted_winners), sorted(query_predicted_winners)
        )

        # When models disagree, it inverts predictions from non-principal models
        non_principal_prediction_type = MLModel.objects.get(
            is_principal=False, used_in_competitions=True
        ).prediction_type

        if non_principal_prediction_type == "Margin":
            non_principal_prediction_label = "predictedMargin"
            draw_prediction = 0
        else:
            non_principal_prediction_label = "predictedWinProbability"
            draw_prediction = 0.5

        predicted_losses = [
            pred[non_principal_prediction_label] <= draw_prediction
            for pred in data["matchPredictions"]
        ]

        self.assertTrue(all(predicted_losses))

        with self.subTest("for unplayed matches"):
            max_round_number = max([match.round_number for match in latest_matches])

            for _ in range(MATCH_COUNT):
                FullMatchFactory(
                    with_predictions=True,
                    future=True,
                    round_number=max_round_number + 1,
                    prediction__ml_model=ml_models[0],
                    prediction_two__ml_model=ml_models[1],
                )

            executed = self.client.execute(query_string)
            data = executed["data"]["fetchLatestRoundPredictions"]

            # It returns isCorrect values of null/None
            unique_is_correct_values = {
                pred["isCorrect"] for pred in data["matchPredictions"]
            }
            self.assertEqual(set([None]), unique_is_correct_values)

            with self.subTest("that don't have predictions yet"):
                Prediction.objects.filter(
                    match__start_date_time__gt=timezone.now()
                ).delete()

                executed = self.client.execute(query_string)
                data = executed["data"]["fetchLatestRoundPredictions"]

                # It returns predictions from the last round that has them
                self.assertEqual(data["roundNumber"], max_round_number)

        with self.subTest("without predictions from a non-principal model"):
            Prediction.objects.filter(ml_model__is_principal=False).delete()

            executed = self.client.execute(query_string)
            data = executed["data"]["fetchLatestRoundPredictions"]

            self.assertGreater(len(data["matchPredictions"]), 0)

    # Keeping this in a separate test, because it requires special setup
    # to properly test metric calculations
    def test_fetch_season_model_metrics_cumulative_metrics(self):
        ml_models = list(MLModel.objects.filter(name__in=MODEL_NAMES))
        YEAR = TWENTY_SEVENTEEN
        MONTH = 6

        for round_n in range(ROUND_COUNT):
            for match_n in range(MATCH_COUNT):
                FullMatchFactory(
                    with_predictions=True,
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

        with self.subTest("for a 'Win Probability' model"):
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

        with self.subTest("for a 'Margin' model"):
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

        with self.subTest("when the last matches in the DB haven't been played yet"):
            DAY = 3
            fake_datetime = timezone.make_aware(datetime(YEAR, MONTH, DAY))

            with freeze_time(fake_datetime):
                # Need to set scores for "future" matches to 0
                TeamMatch.objects.filter(
                    match__start_date_time__gte=fake_datetime
                ).update(score=0)
                Match.objects.filter(start_date_time__gte=fake_datetime).update(
                    winner=None, margin=None
                )

                past_executed = self.client.execute(
                    query, variables={"mlModelName": "predictanator"}
                )

                data = past_executed["data"]["fetchSeasonModelMetrics"][
                    "roundModelMetrics"
                ][0]

                max_match_round = max(
                    Match.objects.all(), key=lambda match: match.round_number
                ).round_number
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
                        isPrincipal
                    }
                }
            """

            data = self.client.execute(query)["data"]["fetchMlModels"]

            self.assertEqual(len(data), len(MODEL_NAMES))
            self.assertLess(len(data), MLModel.objects.count())

            for model in data:
                self.assertTrue(model["usedInCompetitions"])

        with self.subTest("when predictionYear is provided"):
            year = np.random.choice(range(*YEAR_RANGE))
            query = f"""
                query QueryType {{
                    fetchMlModels(predictionYear: {year}) {{
                        name
                    }}
                }}
            """

            ml_models_for_year = (
                MLModel.objects.prefetch_related("prediction_set")
                .filter(prediction__match__start_date_time__year=year)
                .distinct("name")
                .values_list("name", flat=True)
            )

            response = self.client.execute(query)
            data = response["data"]["fetchMlModels"]
            fetched_ml_models = [datum["name"] for datum in data]

            self.assertEqual(len(ml_models_for_year), len(fetched_ml_models))
            self.assertEqual(set(ml_models_for_year), set(fetched_ml_models))

    def test_fetch_latest_round_metrics(self):
        ml_models = list(MLModel.objects.filter(name__in=MODEL_NAMES))
        YEAR = TWENTY_SEVENTEEN
        MONTH = 6

        for round_n in range(ROUND_COUNT):
            for match_n in range(MATCH_COUNT):
                FullMatchFactory(
                    with_predictions=True,
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
            query {
                fetchLatestRoundMetrics {
                    season
                    roundNumber
                    cumulativeCorrectCount
                    cumulativeAccuracy
                    cumulativeMeanAbsoluteError
                    cumulativeMarginDifference
                    cumulativeBits
                }
            }
        """

        executed = self.client.execute(query)
        data = executed["data"]["fetchLatestRoundMetrics"]

        self.assertEqual(data["season"], YEAR)
        self.assertEqual(data["roundNumber"], ROUND_COUNT)

        # We force all predictions to be correct, so the correct count should just be
        # the number of matches
        self.assertEqual(data["cumulativeCorrectCount"], ROUND_COUNT * MATCH_COUNT)
        self.assertGreater(data["cumulativeMeanAbsoluteError"], 0)
        self.assertEqual(
            round(data["cumulativeMarginDifference"]),
            round(data["cumulativeMeanAbsoluteError"] * ROUND_COUNT * MATCH_COUNT),
        )
        self.assertGreater(data["cumulativeAccuracy"], 0)
        # Bits can be positive or negative, so we just want to make sure it's not 0,
        # which would suggest a problem
        self.assertNotEqual(data["cumulativeBits"], 0)

        with self.subTest("when the last matches don't have updated results yet"):
            TeamMatch.objects.filter(
                match__start_date_time__year=YEAR, match__round_number=ROUND_COUNT
            ).update(score=0)

            executed = self.client.execute(query)
            data = executed["data"]["fetchLatestRoundMetrics"]

            # It fetches latest round with results
            self.assertEqual(data["roundNumber"], ROUND_COUNT - 1)

        with self.subTest("when the last matches haven't been played yet"):
            DAY = 3
            fake_datetime = timezone.make_aware(datetime(YEAR, MONTH, DAY))

            with freeze_time(fake_datetime):
                past_executed = self.client.execute(
                    query, variables={"mlModelName": "predictanator"}
                )

                data = past_executed["data"]["fetchLatestRoundMetrics"]

                max_match_round = max(
                    Match.objects.all(), key=lambda match: match.round_number
                ).round_number
                self.assertLess(data["roundNumber"], max_match_round)
                # Last played match will be from day before, because "now" and the
                # start time for "today's match" are equal
                self.assertEqual(data["roundNumber"], DAY - 1)

                self.assertGreater(data["cumulativeCorrectCount"], 0)
                self.assertGreater(data["cumulativeMeanAbsoluteError"], 0)
                self.assertGreater(data["cumulativeMarginDifference"], 0)

        with self.subTest("when predicted_win_probability is all blank"):
            Prediction.objects.all().update(predicted_win_probability=None)
            MLModel.objects.filter(is_principal=False).delete()

            executed = self.client.execute(query)
            data = executed["data"]["fetchLatestRoundMetrics"]

            self.assertEqual(data["cumulativeBits"], 0)

    def _assert_correct_prediction_results(self, results, expected_results):
        sorted_results = self._sort_results(results)
        sorted_expected_results = self._sort_results(expected_results)
        # graphene returns OrderedDicts instead of dicts, which makes asserting
        # on results a little more complicated
        for idx, result in enumerate(sorted_results):
            expected_result = sorted_expected_results[idx]

            self.assertEqual(dict(result["match"]), expected_result["match"])
            self.assertEqual(dict(result["mlModel"]), expected_result["mlModel"])
            self.assertEqual(result["isCorrect"], expected_result["isCorrect"])

    @staticmethod
    def _sort_results(results):
        return sorted(
            sorted(
                sorted(results, key=lambda result: result["mlModel"]["name"]),
                key=lambda result: result["match"]["roundNumber"],
            ),
            key=lambda result: result["match"]["year"],
        )
