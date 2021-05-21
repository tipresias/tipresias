# pylint: disable=missing-docstring

import numpy as np
import pandas as pd
import responses
import pytest

from tests.fixtures import data_factories
from tipping import data_export, settings


N_MATCHES = 5


@responses.activate
@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (200, None),
        (301, data_export.DataExportError),
        (404, data_export.DataExportError),
        (500, data_export.ServerErrorResponse),
    ],
)
def test_update_fixture_data(status_code, expected_error):
    responses.add(
        responses.POST,
        f"{settings.TIPRESIAS_APP}/fixtures",
        status=status_code,
        json="Stuff happened",
    )

    fake_fixture = data_factories.fake_fixture_data()
    upcoming_round = np.random.randint(1, 24)

    if expected_error is None:
        data_export.update_fixture_data(fake_fixture, upcoming_round)
    else:
        with pytest.raises(expected_error, match=str(status_code)):
            data_export.update_fixture_data(fake_fixture, upcoming_round)


@responses.activate
@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (200, None),
        (301, data_export.DataExportError),
        (404, data_export.DataExportError),
        (500, data_export.ServerErrorResponse),
    ],
)
def test_update_match_predictions(status_code, expected_error):
    response_data = [
        {
            "predicted_winner__name": "Some Team",
            # Can't use 'None' for either prediction value, because it messes
            # with pandas equality checks
            "predicted_margin": 5.23,
            "predicted_win_probability": 0.876,
        }
    ]
    responses.add(
        responses.POST,
        f"{settings.TIPRESIAS_APP}/predictions",
        status=status_code,
        json=response_data,
    )

    fake_predictions = pd.concat(
        [data_factories.fake_prediction_data() for _ in range(N_MATCHES)]
    )

    if expected_error is None:
        prediction_records = data_export.update_match_predictions(fake_predictions)

        # It returns the created/updated predictions records
        assert (prediction_records == pd.DataFrame(response_data)).all().all()
    else:
        with pytest.raises(expected_error, match=str(status_code)):
            data_export.update_match_predictions(fake_predictions)


@responses.activate
@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (200, None),
        (301, data_export.DataExportError),
        (404, data_export.DataExportError),
        (500, data_export.ServerErrorResponse),
    ],
)
def test_update_matches(status_code, expected_error):
    responses.add(
        responses.POST,
        f"{settings.TIPRESIAS_APP}/matches",
        status=status_code,
        json="Stuff happened",
    )

    fake_matches = data_factories.fake_match_data()

    if expected_error is None:
        data_export.update_matches(fake_matches)
    else:
        with pytest.raises(expected_error, match=str(status_code)):
            data_export.update_matches(fake_matches)


@responses.activate
@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (200, None),
        (301, data_export.DataExportError),
        (404, data_export.DataExportError),
        (500, data_export.ServerErrorResponse),
    ],
)
def test_update_match_results(status_code, expected_error):
    responses.add(
        responses.POST,
        f"{settings.TIPRESIAS_APP}/matches",
        status=status_code,
        json="Stuff happened",
    )

    fake_match_results = data_factories.fake_match_results_data()

    if expected_error is None:
        data_export.update_match_results(fake_match_results)
    else:
        with pytest.raises(expected_error, match=str(status_code)):
            data_export.update_match_results(fake_match_results)
