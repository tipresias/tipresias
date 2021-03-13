# pylint: disable=missing-docstring,redefined-outer-name

from datetime import datetime

import pytest
import responses

from tipping import data_import
from tipping import settings


@pytest.fixture
def data_importer():
    return data_import.DataImporter()


@pytest.fixture
def response_data():
    return {"data": [{"date": "2020-03-01"}]}


@pytest.mark.parametrize(
    "start_date,end_date",
    [
        ("24-05-2021", "2021-05-24"),
        (str(datetime.now()), "2021-05-24"),
        ("2020-05-24", str(datetime.now())),
    ],
)
def test_invalid_fetch_match_data_params(start_date, end_date, data_importer):
    with pytest.raises(AssertionError, match="yyyy-mm-dd"):
        data_importer.fetch_match_data(start_date, end_date)


@responses.activate
@pytest.mark.parametrize(
    "status_code,expected_error",
    [
        (200, None),
        (301, data_import.DataImportError),
        (404, data_import.DataImportError),
        (500, data_import.ServerErrorResponse),
    ],
)
def test_responses(status_code, expected_error, data_importer, response_data):
    responses.add(
        responses.GET,
        f"{settings.DATA_SCIENCE_SERVICE}/fixtures",
        status=status_code,
        json=response_data,
    )

    if expected_error is None:
        data_importer.fetch_fixture_data(datetime.now(), datetime.now())
    else:
        with pytest.raises(expected_error, match=str(status_code)):
            data_importer.fetch_fixture_data(datetime.now(), datetime.now())
