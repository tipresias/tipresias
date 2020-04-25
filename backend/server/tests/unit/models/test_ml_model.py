# pylint: disable=missing-docstring
from django.test import TestCase
from django.core.exceptions import ValidationError

from server.models import MLModel


class TestMLModel(TestCase):
    def setUp(self):
        self.ml_model = MLModel(name="test_estimator")

    def test_validation(self):
        with self.subTest("when the model name already exists"):
            self.ml_model.save()

            duplicate_model = MLModel(name="test_estimator")

            with self.assertRaises(ValidationError):
                duplicate_model.full_clean()
