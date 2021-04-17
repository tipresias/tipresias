# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone

import numpy as np
from faker import Faker

from tipping.models.match import Match


FAKE = Faker()


def test_match_creation(fauna_session):
    match = Match(
        start_date_time=FAKE.date_time(tzinfo=timezone.utc),
        round_number=np.random.randint(1, 100),
        venue=FAKE.company(),
    )
    fauna_session.add(match)
    fauna_session.commit()

    assert match.id is not None
