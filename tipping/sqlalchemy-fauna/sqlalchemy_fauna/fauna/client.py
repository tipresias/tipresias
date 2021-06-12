# pylint: disable=too-many-lines

"""Module for all FaunaDB functionality."""

from typing import Union, Any, Dict, List, Optional, Tuple, cast, Sequence
from time import sleep
import logging
from datetime import datetime
import re

from faunadb import client
from faunadb import query as q, errors as fauna_errors
from faunadb.objects import FaunaTime, Ref
from faunadb.objects import _Expr as QueryExpression
import sqlparse
from sqlparse import tokens as token_types
from sqlparse import sql as token_groups
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions
from . import translation
from .translation.common import extract_value


SQLResult = List[Dict[str, Any]]
FieldMetadata = TypedDict(
    "FieldMetadata",
    {
        "unique": bool,
        "not_null": bool,
        "default": Union[str, int, float, bool, datetime, None],
        "type": str,
    },
)
FieldsMetadata = Dict[str, FieldMetadata]
CollectionMetadata = TypedDict("CollectionMetadata", {"fields": FieldsMetadata})
IndexComparison = Tuple[str, Union[int, float, str, None, datetime]]
Comparisons = TypedDict(
    "Comparisons",
    {"by_id": Optional[Union[int, str]], "by_index": List[IndexComparison]},
)

DATA_TYPE_MAP = {
    "CHAR": "String",
    "VARCHAR": "String",
    "BINARY": "String",
    "VARBINARY": "String",
    "TINYBLOB": "String",
    "TINYTEXT": "String",
    "TEXT": "String",
    "BLOB": "String",
    "MEDIUMTEXT": "String",
    "MEDIUMBLOB": "String",
    "LONGTEXT": "String",
    "LONGBLOB": "String",
    "ENUM": "String",
    "SET": "String",
    "BIT": "Integer",
    "TINYINT": "Integer",
    "SMALLINT": "Integer",
    "MEDIUMINT": "Integer",
    "INT": "Integer",
    "INTEGER": "Integer",
    "BIGINT": "Integer",
    "FLOAT": "Float",
    "DOUBLE": "Float",
    "DOUBLE PRECISION": "Float",
    "DECIMAL": "Float",
    "DEC": "Float",
    "BOOL": "Boolean",
    "BOOLEAN": "Boolean",
    "YEAR": "Integer",
    "DATE": "Date",
    "DATETIME": "TimeStamp",
    "TIMESTAMP": "TimeStamp",
    # Fauna has no concept of time independent of the date
    "TIME": "String",
}

DEFAULT_FIELD_METADATA: FieldMetadata = {
    "unique": False,
    "not_null": False,
    "default": None,
    "type": "",
}

ALEMBIC_INDEX_PREFIX_REGEX = re.compile(r"^ix_")


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
        (
            fql_query,
            column_names,
            alias_names,
        ) = translation.translate_sql_to_fql(sql_query)
        result = self._client.query(fql_query)

        if table_name == "INFORMATION_SCHEMA.TABLES":
            collections = result["data"]

            return [
                self._fauna_reference_to_dict(collection["ref"])
                for collection in collections
            ]

        if table_name == "INFORMATION_SCHEMA.COLUMNS":
            # Selecting column info from INFORMATION_SCHEMA returns foreign keys
            # as regular columns, so we don't need the extra table-reference info
            remove_references = lambda field_data: {
                key: value for key, value in field_data.items() if key != "references"
            }

            return [
                {**remove_references(field_data), "name": field_name}
                for field_name, field_data in result.items()
            ]

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

        column_alias_map = {
            column: alias or column for column, alias in zip(column_names, alias_names)
        }

        columns = [
            self._select_columns(
                list(column_alias_map.values()),
                self._fauna_data_to_dict(data, alias_map=column_alias_map),
            )
            for data in result["data"]
        ]

        if len(columns):
            assert len(columns[0]) == len(column_names) == len(alias_names), (
                "Something went wrong with translating between SQL columns and FQL fields:\n"
                f"FQL field names: {column_names}\n"
                f"SQL column aliases: {alias_names}\n"
                f"First row of results: {columns[0]}"
            )

        return columns

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

        return [self._fauna_data_to_dict(result)]

    def _execute_delete(self, sql_query: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)
        results = self._client.query(fql_query)

        return [self._clean_fauna_key_values(results["data"])]

    def _execute_update(self, sql_query: str) -> SQLResult:
        fql_query = translation.translate_sql_to_fql(sql_query)
        result = self._client.query(fql_query)

        return [{"count": result}]

    def _convert_terms_to_column_names(self, index: Dict[str, Any]) -> List[str]:
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

    def _parse_identifiers(
        self, identifiers: Union[token_groups.Identifier, token_groups.IdentifierList]
    ) -> Tuple[Sequence[Optional[str]], Sequence[str], Sequence[Optional[str]]]:
        if isinstance(identifiers, token_groups.Identifier):
            table_name, column_name, alias_name = self._parse_identifier(identifiers)
            return ((table_name,), (column_name,), (alias_name,))

        return cast(
            Tuple[Sequence[Optional[str]], Sequence[str], Sequence[Optional[str]]],
            tuple(
                zip(
                    *[
                        self._parse_identifier(identifier)
                        for identifier in identifiers
                        if isinstance(identifier, token_groups.Identifier)
                    ]
                )
            ),
        )

    @staticmethod
    def _parse_identifier(
        identifier: token_groups.Identifier,
    ) -> Tuple[Optional[str], str, Optional[str]]:
        idx, identifier_name = identifier.token_next_by(t=token_types.Name)

        tok_idx, next_token = identifier.token_next(idx, skip_ws=True)
        if next_token and next_token.match(token_types.Punctuation, "."):
            idx = tok_idx
            table_name = identifier_name.value
            idx, column_identifier = identifier.token_next_by(
                t=token_types.Name, idx=idx
            )
            column_name = column_identifier.value
        else:
            table_name = None
            column_name = identifier_name.value

        idx, as_keyword = identifier.token_next_by(
            m=(token_types.Keyword, "AS"), idx=idx
        )

        if as_keyword is not None:
            _, alias_identifier = identifier.token_next_by(
                i=token_groups.Identifier, idx=idx
            )
            alias_name = alias_identifier.value
        else:
            alias_name = None

        return (table_name, column_name, alias_name)

    @staticmethod
    def _extract_value(token: token_groups.Token) -> Union[str, int, float, None]:
        value = token.value

        if value == "NONE":
            return None

        if isinstance(value, str):
            return value.replace("'", "")

        return value

    @staticmethod
    def _fauna_reference_to_dict(ref: Ref) -> Dict[str, Any]:
        ref_dict = {}

        for key, value in ref.value.items():
            if key == "metadata":
                continue

            if isinstance(value, Ref):
                ref_dict[f"{key}_id"] = value.id()
                continue

            ref_dict[key] = value

        return ref_dict

    def _fauna_data_to_dict(
        self, data: Dict[str, Any], alias_map: Dict[str, str] = None
    ) -> Dict[str, Any]:
        sql_dict = self._clean_fauna_key_values(
            {"id": data["ref"].id(), **data}, alias_map=alias_map
        )
        # SELECT queries usually include a nested 'data' object for the selected values,
        # but selecting TABLE_NAMES does not, and there might be other cases
        # that I haven't encountered yet.
        sub_data = self._clean_fauna_key_values(
            data.get("data", {}), alias_map=alias_map
        )

        return {
            **sql_dict,
            **sub_data,
        }

    @staticmethod
    def _clean_fauna_key_values(
        fauna_data: Dict[str, Any], alias_map: Dict[str, str] = None
    ) -> Dict[str, Any]:
        alias_map = alias_map or {}
        clean_fauna_data = {}

        for key, value in fauna_data.items():
            if key in ("ref", "data"):
                continue

            queried_key = alias_map.get(key) or key
            clean_fauna_data[queried_key] = (
                value.to_datetime() if isinstance(value, FaunaTime) else value
            )

        return clean_fauna_data

    @staticmethod
    def _select_columns(
        column_names: Sequence[str], document: Dict[str, Any]
    ) -> Dict[str, Any]:
        # TODO: We'll need a way to fill in blank fields when the query has 'SELECT *'
        if column_names[0] == "*":
            return document

        # We need to fill in blank columns, because Fauna doesn't return fields
        # with null values in query responses
        blank_columns = {column_name: None for column_name in column_names}
        returned_columns = {
            key: value for key, value in document.items() if key in column_names
        }

        return {
            **blank_columns,
            **returned_columns,
        }
