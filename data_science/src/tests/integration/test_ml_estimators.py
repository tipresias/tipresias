from unittest import TestCase
from sklearn.externals import joblib

from machine_learning.ml_estimators.base_ml_estimator import BaseMLEstimator

PICKLE_FILEPATHS = [
    "src/machine_learning/ml_estimators/bagging_estimator/tipresias.pkl",
    "src/machine_learning/ml_estimators/benchmark_estimator/benchmark_estimator.pkl",
]


class TestMLEstimators(TestCase):
    """Basic spot check for being able to load saved ML estimators"""

    def setUp(self):
        self.estimators = [joblib.load(filepath) for filepath in PICKLE_FILEPATHS]

    def test_estimator_validity(self):
        for estimator in self.estimators:
            self.assertIsInstance(estimator, BaseMLEstimator)
