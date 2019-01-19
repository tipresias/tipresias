import os
from django.test import TestCase
from django.core.exceptions import ValidationError
from sklearn.base import BaseEstimator

from server.models import MLModel
from project.settings import BASE_DIR


class TestMLModel(TestCase):
    def setUp(self):
        pickle_path = os.path.join(
            BASE_DIR, "server", "tests", "fixtures", "betting_model.pkl"
        )
        self.ml_model = MLModel(name="my_estimator", filepath=pickle_path)

    def test_validation(self):
        with self.subTest("when the data_class_path isn't a module path"):
            self.ml_model.data_class_path = "some/bad/path"

            with self.assertRaises(ValidationError):
                self.ml_model.full_clean()

        with self.subTest("when the model name already exists"):
            self.ml_model.data_class_path = "some.perfectly.fine.path"
            self.ml_model.save()

            duplicate_model = MLModel(name="my_estimator")

            with self.assertRaises(ValidationError):
                duplicate_model.full_clean()

    def test_load_estimator(self):
        loaded_model = self.ml_model.load_estimator()

        self.assertIsInstance(loaded_model, BaseEstimator)
