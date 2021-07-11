# pylint: disable=too-many-lines

"""Module for all FaunaDB functionality."""

import typing
from time import sleep
import logging
from datetime import datetime

from faunadb import client, errors as fauna_errors
from faunadb.objects import FaunaTime, Ref, _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import translation


SQLResult = typing.List[typing.Dict[str, typing.Any]]


class FaunaClientError(Exception):
    """Errors raised by the FaunaClient while executing queries."""


class FaunaClient:
    """API client for calling FaunaDB endpoints."""

    def __init__(self, secret=None, scheme="http", domain="faunadb", port=8443):
        """
        Params:
        -------
        secret: API key to use to access a FaunaDB database.
        scheme: Which scheme to use when calling the database ('http' or 'https').
        domain: Domain of the database server.
        port: Port used by the database server.
        """
        self._client = client.FaunaClient(
            scheme=scheme, domain=domain, port=port, secret=secret
        )

    def sql(self, query: str) -> SQLResult:
        """Convert SQL to FQL and execute the query."""
        formatted_query = translation.format_sql_query(query)

        try:
            return self._execute_sql(formatted_query)
        except Exception as err:
            logging.error("\n%s", formatted_query)
            raise err

    def _execute_sql(self, sql_query: str) -> SQLResult:
        fql_queries = translation.translate_sql_to_fql(sql_query)

        try:
            for fql_query in fql_queries:
                result = self._execute_with_retries(fql_query)
        except fauna_errors.BadRequest as err:
            if "document is not unique" not in str(err):
                raise err

            # TODO: this isn't a terribly helpful error message, but executing the queries
            # to make a better one is a little tricky, so leaving it as-is for now.
            raise exceptions.ProgrammingError(
                "Tried to create a document with duplicate value for a unique field."
            )

        return [self._fauna_data_to_sqlalchemy_result(data) for data in result["data"]]

    def _execute_with_retries(
        self,
        query: QueryExpression,
        retries: int = 0,
    ):
        # Sometimes Fauna needs time to do something when trying to create collections,
        # so we retry with gradual backoff. This seems to only be an issue when
        # creating/deleting collections in quick succession, so might not matter
        # in production where that happens less frequently.
        try:
            return self._client.query(query)
        except fauna_errors.BadRequest as err:
            if "document data is not valid" not in str(err) or retries >= 10:
                raise err

            sleep(retries * 2)
            return self._execute_with_retries(query, retries=(retries + 1))

    def _fauna_data_to_sqlalchemy_result(
        self, data: typing.Dict[str, typing.Union[str, bool, int, float, datetime]]
    ) -> typing.Dict[str, typing.Any]:
        return {
            key: self._convert_fauna_to_python(value) for key, value in data.items()
        }

    @staticmethod
    def _convert_fauna_to_python(
        value: typing.Any,
    ) -> typing.Union[str, bool, int, float, datetime]:
        assert not isinstance(value, (list, dict, tuple))

        if isinstance(value, Ref):
            return value.id()

        if isinstance(value, FaunaTime):
            return value.to_datetime()

        return value
