"""One-off script for filling in correct values for new MLModel fields."""

import os
import sys

import django

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from server.models import MLModel  # pylint: disable=wrong-import-position
from server.models.ml_model import (  # pylint: disable=wrong-import-position
    PredictionType,
)

PRINCIPAL_MODEL_NAME = "tipresias_2020"
COMPETITION_MODEL_NAMES = ["tipresias_2020", "confidence_estimator"]
CONFIDENCE_MODELS = ["confidence_estimator"]


def main():
    """Run the script for backfilling values."""
    for ml_model in MLModel.objects.all():
        if ml_model.name == PRINCIPAL_MODEL_NAME:
            ml_model.is_principal = True

        if ml_model.name in COMPETITION_MODEL_NAMES:
            ml_model.used_in_competitions = True

        if ml_model.name in CONFIDENCE_MODELS:
            ml_model.prediction_type = PredictionType.WIN_PROBABILITY

        ml_model.full_clean()
        ml_model.save()


if __name__ == "__main__":
    main()
