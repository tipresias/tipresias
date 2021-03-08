# pylint: disable=missing-docstring,redefined-outer-name

from datetime import datetime

import pytest

from tipping import data_import


@pytest.fixture()
def data_importer():
    return data_import.DataImporter()


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
