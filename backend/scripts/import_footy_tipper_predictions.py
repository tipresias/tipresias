"""One-off script to import Footy Tipper predictions to the DB."""

import os
import sys
import json

import django

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from server.models import Prediction  # pylint: disable=wrong-import-position


def main():
    """One-off script to import Footy Tipper predictions to the DB."""
    with open(
        os.path.join(PROJECT_PATH, "data/footy_tipper_predictions_2018.json")
    ) as file:
        predictions = json.load(file)

        for pred in predictions:
            Prediction.update_or_create_from_raw_data(pred, future_only=False)


if __name__ == "__main__":
    main()
