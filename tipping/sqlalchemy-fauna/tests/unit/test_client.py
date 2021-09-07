# pylint: disable=missing-docstring,redefined-outer-name

from unittest import mock

import pytest
from faunadb import errors

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna import client


def _define_request_result(status_code, response_description):
    request_result = mock.MagicMock()
    request_result.status_code = status_code
    request_result.response_content = {
        "errors": [
            {
                "position": [
                    "let",
                    0,
                    "maybe_documents",
                    "paginate",
                    "intersection",
                    "match",
                ],
                "code": "invalid ref",
                "description": response_description,
            }
        ]
    }
    return request_result


@mock.patch("faunadb.client.FaunaClient.query")
def test_undefined_index_error(mock_query):
    table_name = "users"
    request_result = _define_request_result(
        400, f"Ref refers to undefined index '{table_name}_all'"
    )
    mock_query.side_effect = errors.BadRequest(request_result)
    sql_string = f"SELECT name FROM {table_name}"
    fauna_client = client.FaunaClient()

    with pytest.raises(exceptions.InternalError):
        fauna_client.sql(sql_string)


@mock.patch("faunadb.client.FaunaClient.query")
def test_undefined_index_error_information_schema(mock_query):
    table_name = "information_schema_tables_"
    request_result = _define_request_result(
        400, f"Ref refers to undefined index '{table_name}_all'"
    )
    mock_query.side_effect = errors.BadRequest(request_result)
    sql_string = f"SELECT name_ FROM {table_name}"
    fauna_client = client.FaunaClient()

    result = fauna_client.sql(sql_string)
    assert not any(result)
