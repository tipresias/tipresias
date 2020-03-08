# pylint: disable=missing-docstring
from django.test import TestCase
from django.core.exceptions import ValidationError

from server.models import MLModel


class TestMLModel(TestCase):
    def setUp(self):
        self.ml_model = MLModel(
            name="test_estimator", filepath="path/to/test_estimator.pkl"
        )

    def test_validation(self):
        with self.subTest("when the data_class_path isn't a module path"):
            self.ml_model.data_class_path = "some/bad/path"

            with self.assertRaises(ValidationError):
                self.ml_model.full_clean()

        with self.subTest("when the model name already exists"):
            self.ml_model.data_class_path = "some.perfectly.fine.path"
            self.ml_model.save()

            duplicate_model = MLModel(name="test_estimator")

            with self.assertRaises(ValidationError):
                duplicate_model.full_clean()
