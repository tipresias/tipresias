# pylint: disable=too-many-lines

"""Module for all FaunaDB functionality."""

import typing
from time import sleep
import logging
from datetime import datetime

from faunadb import client
from faunadb import query as q, errors as fauna_errors
from faunadb.objects import FaunaTime, Ref, _Expr as QueryExpression
import sqlparse
from sqlparse import tokens as token_types
from sqlparse import sql as token_groups

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
        sql_statements = sqlparse.parse(formatted_query)

        if len(sql_statements) > 1:
            raise exceptions.NotSupportedError(
                "Only one SQL statement at a time is currently supported. "
                f"The following query has more than one:\n{formatted_query}"
            )

        sql_statement = sql_statements[0]

        try:
            return self._execute_sql_statement(sql_statement)
        except Exception as err:
            logging.error("\n%s", formatted_query)
            raise err

    def _execute_sql_statement(self, statement: token_groups.Statement) -> SQLResult:
        sql_query = str(statement)

        if statement.token_first().match(token_types.DML, "SELECT"):
            table_name = self._extract_table_name(statement)
            return self._execute_select(sql_query, table_name)

        if statement.token_first().match(token_types.DDL, "CREATE"):
            return self._execute_create(sql_query)

        if statement.token_first().match(token_types.DDL, "DROP"):
            return self._execute_drop(sql_query)

        if statement.token_first().match(token_types.DML, "INSERT"):
            return self._execute_insert(sql_query)

        if statement.token_first().match(token_types.DML, "DELETE"):
            return self._execute_delete(sql_query)

        if statement.token_first().match(token_types.DML, "UPDATE"):
            return self._execute_update(sql_query)

        raise exceptions.NotSupportedError()

    def _execute_select(self, sql_query: str, table_name: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)
        result = self._client.query(fql_query)

        if table_name == "INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE":
            return [
                {
                    "name": index["name"],
                    "column_names": ",".join(
                        self._convert_terms_to_column_names(index)
                    ),
                    # Fauna doesn't seem to return a 'unique' field with index queries,
                    # and we don't really need it, so leaving it blank for now.
                    "unique": False,
                }
                for index in result["data"]
            ]

        # If an index match only returns one document, the result is a dictionary,
        # otherwise, it's a dictionary wrapped in a list. Not sure why,
        # as fetching by ID returns a list when paginated & mapped, and too lazy
        # to figure it out.
        try:
            result = result[0]
        except KeyError:
            pass

        return [self._fauna_data_to_sqlalchemy_result(data) for data in result["data"]]

    def _execute_create(self, sql_query: str) -> SQLResult:
        fql_queries = translation.translate_sql_to_fql(sql_query)

        for fql_query in fql_queries:
            result = self._execute_create_with_retries(fql_query)

        # We only return info from the final result, because even though we require
        # multiple FQL queries, this is only one SQL query.
        collection = result if isinstance(result, Ref) else result[-1]
        return [self._fauna_reference_to_dict(collection)]

    def _execute_drop(self, sql_query: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)
        result = self._client.query(fql_query)
        return [self._fauna_reference_to_dict(result["ref"])]

    def _execute_insert(self, sql_query: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)

        try:
            result = self._client.query(fql_query)
        except fauna_errors.BadRequest as err:
            if "document is not unique" not in str(err):
                raise err

            # TODO: this isn't a terribly helpful error message, but executing the queries
            # to make a better one is a little tricky, so leaving it as-is for now.
            raise exceptions.ProgrammingError(
                "Tried to create a document with duplicate value for a unique field."
            )

        return [self._fauna_data_to_sqlalchemy_result(result)]

    def _execute_delete(self, sql_query: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)
        result = self._client.query(fql_query)

        return [self._fauna_data_to_sqlalchemy_result(result["data"])]

    def _execute_update(self, sql_query: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)
        result = self._client.query(fql_query)

        return [{"count": result}]

    def _convert_terms_to_column_names(
        self, index: typing.Dict[str, typing.Any]
    ) -> typing.List[str]:
        terms = index.get("terms")

        if terms is not None:
            return [term["field"][-1] for term in terms]

        source_collection = index["source"].id()
        collection_fields = self._client.query(
            q.select(
                ["data", "metadata", "fields"],
                q.get(q.collection(source_collection)),
            )
        )

        return [field_name for field_name in collection_fields.keys()]

    @staticmethod
    def _extract_table_name(statement: token_groups.Statement) -> str:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
        _, table_identifier = statement.token_next_by(
            i=(token_groups.Identifier), idx=idx
        )
        return table_identifier.value

    def _execute_create_with_retries(
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

            sleep(retries)
            return self._execute_create_with_retries(query, retries=(retries + 1))

    @staticmethod
    def _fauna_reference_to_dict(ref: Ref) -> typing.Dict[str, typing.Any]:
        ref_dict = {}

        for key, value in ref.value.items():
            if key == "metadata":
                continue

            if isinstance(value, Ref):
                ref_dict[f"{key}_id"] = value.id()
                continue

            ref_dict[key] = value

        return ref_dict

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
