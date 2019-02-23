from django.test import TestCase

from server.ml_models.betting_model import BettingModel, BettingModelData
from server.ml_models.match_model import MatchModel, MatchModelData
from server.ml_models.all_model import AllModel, AllModelData
from server.ml_models.ensemble_model import EnsembleModel
from server.tests.helpers import regression_accuracy


class TestMLModels(TestCase):
    def setUp(self):
        self.estimators = [
            (
                BettingModel(),
                BettingModelData(train_years=(2010, 2015), test_years=(2016, 2016)),
            ),
            (
                MatchModel(),
                MatchModelData(train_years=(2010, 2015), test_years=(2016, 2016)),
            ),
            (
                AllModel(),
                AllModelData(train_years=(2010, 2015), test_years=(2016, 2016)),
            ),
            (
                EnsembleModel(),
                AllModelData(train_years=(2010, 2015), test_years=(2016, 2016)),
            ),
        ]

    def test_model_and_data(self):
        for estimator, data in self.estimators:
            test_label = (
                estimator.__class__.__name__ + " and " + data.__class__.__name__
            )

            with self.subTest(test_label):
                X_train, y_train = data.train_data()
                estimator.fit(X_train, y_train)
                X_test, y_test = data.test_data()
                y_pred = estimator.predict(X_test)

                unique_predictions = set(y_pred)

                # If all the predictions are the same, something went horribly wrong
                self.assertNotEqual(len(unique_predictions), 1)

                accuracy = regression_accuracy(y_test, y_pred)

                # A spot check for leaking data from the match-to-predict
                # (i.e. accidentally including data from 'future' matches in a data row
                # that the model is predicting on).
                # The threshold might change if the models get better, but for now,
                # whenever I see accuracy > 80%, it's always been due to a mistake
                # of this nature.
                self.assertLess(accuracy, 0.8)
