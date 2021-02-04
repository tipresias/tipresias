# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import pytest
from faker import Faker
import numpy as np

from tipping.models.match import Match, ValidationError


FAKE = Faker()


@pytest.mark.parametrize(
    "attribute,error_message",
    [
        ({"round_number": np.random.randint(-100, 1)}, r"round_number"),
        ({"margin": np.random.randint(-100, 0)}, r"margin"),
        ({"start_date_time": FAKE.date_time()}, r"start_date_time"),
    ],
)
def test_match_validation(attribute, error_message):
    default_input = {
        "start_date_time": FAKE.date_time(tzinfo=timezone.utc),
        "venue": FAKE.street_name(),
        "margin": np.random.randint(0, 100),
        "round_number": np.random.randint(1, 100),
    }

    with pytest.raises(ValidationError, match=error_message):
        Match(
            **{
                **default_input,
                **attribute,
            }
        )
