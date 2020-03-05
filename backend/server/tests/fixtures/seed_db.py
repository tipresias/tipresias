from datetime import date
from itertools import product
import os
import sys

from django.db import transaction, connections
import django
from django.conf import settings

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

django.setup()

from server.tests.fixtures.factories import FullMatchFactory, MLModelFactory


# There are two predictions per match in the FullMatchFactory, so keeping the MLModel
# count to two, makes sure that each MLModel gets a prediction per match.
N_ML_MODELS = 2
N_SEASONS = 3
N_ROUNDS_PER_SEASON = 10
N_MATCHES_PER_ROUND = 5


def main():
    assert settings.ENVIRONMENT == "test"

    current_year = date.today().year
    first_season = current_year - N_SEASONS + 1

    seasons_rounds_matches = product(
        range(first_season, current_year + 1),
        range(1, N_ROUNDS_PER_SEASON + 1),
        range(N_MATCHES_PER_ROUND),
    )

    connections["default"].creation.create_test_db(autoclobber=True)
    # create_test_db should set the default DB to test_${DATABASE_NAME}
    assert settings.DATABASES["default"]["NAME"] != os.getenv("DATABASE_NAME")

    with transaction.atomic():
        # "tipresias" is the name of the primary MLModel and is hardcoded in various
        # places, so we need at least one MLModel with that name
        MLModelFactory(name="tipresias_2019")

        for _ in range(N_ML_MODELS - 1):
            MLModelFactory()

        for season, round_number, _match in seasons_rounds_matches:
            # We need some future matches for functionality around predictions,
            # so we're arbitrarily making the second half of the current season
            # sometime after today
            future_match = (
                season == date.today().year and round_number > N_ROUNDS_PER_SEASON / 2
            )
            FullMatchFactory(
                year=season, round_number=round_number, future=future_match
            )


if __name__ == "__main__":
    main()
