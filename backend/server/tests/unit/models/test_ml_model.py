# pylint: disable=missing-docstring
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import utils, transaction

from server.models import MLModel


class TestMLModel(TestCase):
    def setUp(self):
        self.ml_model = MLModel(name="test_estimator")

    def test_validation(self):
        with self.subTest("when the model name already exists"):
            self.ml_model.save()

            duplicate_model = MLModel(name="test_estimator")

            with self.assertRaisesMessage(
                ValidationError, "{'name': ['Ml model with this Name already exists.']}"
            ):
                duplicate_model.full_clean()

    def test_clean(self):
        with self.subTest("when a principle model isn't used in competitions"):
            self.ml_model.is_principle = True
            self.ml_model.used_in_competitions = False

            with self.assertRaisesMessage(
                ValidationError, "A principle model must be used for competitions."
            ):
                self.ml_model.full_clean()

    def test_one_principle_model(self):
        """
        Test validation rule for having only one principle model.

        We run this in its own test method, because raising DB-level errors as part
        of a subtest tends to break things, because Django wraps each test method
        in an atomic transaction.
        """
        self.ml_model.is_principle = True
        self.ml_model.used_in_competitions = True
        self.ml_model.save()

        duplicate_model = MLModel(
            name="say_hello_to_the_new_boss",
            is_principle=True,
            used_in_competitions=True,
            prediction_type="Win Probability",
        )

        with self.assertRaisesMessage(
            utils.IntegrityError,
            'duplicate key value violates unique constraint "one_principle_model"\n'
            "DETAIL:  Key (is_principle)=(t) already exists.\n",
        ):
            duplicate_model.full_clean()
            duplicate_model.save()

    def test_unique_competition_prediction_type(self):
        """
        Test validation rule for having only unique prediction types for competitions.

        We run this in its own test method, because raising DB-level errors as part
        of a subtest tends to break things, because Django wraps each test method
        in an atomic transaction.
        """
        self.ml_model.used_in_competitions = True
        self.ml_model.save()

        duplicate_model = MLModel(
            name="another_estimator",
            used_in_competitions=True,
            prediction_type=self.ml_model.prediction_type,
        )

        with self.assertRaisesMessage(
            utils.IntegrityError,
            "duplicate key value violates unique constraint "
            '"unique_prediction_type_for_competitions"\nDETAIL:  '
            "Key (prediction_type)=(Margin) already exists.\n",
        ):
            with transaction.atomic():
                duplicate_model.full_clean()
                duplicate_model.save()
