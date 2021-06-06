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
            return self._execute_drop(statement)

        if statement.token_first().match(token_types.DML, "INSERT"):
            return self._execute_insert(statement)

        if statement.token_first().match(token_types.DML, "DELETE"):
            return self._execute_delete(statement)

        if statement.token_first().match(token_types.DML, "UPDATE"):
            return self._execute_update(statement)

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
            column: alias
            for column, alias in zip(column_names, alias_names)
            if alias is not None
        }

        return [
            self._select_columns(
                column_names,
                self._fauna_data_to_dict(data, alias_map=column_alias_map),
            )
            for data in result["data"]
        ]

    def _execute_create(self, sql_query: str) -> SQLResult:
        fql_queries = translation.translate_sql_to_fql(sql_query)

        for fql_query in fql_queries:
            result = self._execute_create_with_retries(fql_query)

        # We only return info from the final result, because even though we require
        # multiple FQL queries, this is only one SQL query.
        collection = result if isinstance(result, Ref) else result[-1]
        return [self._fauna_reference_to_dict(collection)]

    def _execute_drop(self, statement: token_groups.Statement) -> SQLResult:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "TABLE"))
        _, table_identifier = statement.token_next_by(
            i=token_groups.Identifier, idx=idx
        )

        result = self._client.query(q.delete(q.collection(table_identifier.value)))
        return [self._fauna_reference_to_dict(result["ref"])]

    def _execute_insert(self, statement: token_groups.Statement) -> SQLResult:
        idx, function_group = statement.token_next_by(i=token_groups.Function)
        func_idx, table_identifier = function_group.token_next_by(
            i=token_groups.Identifier
        )
        table_name = table_identifier.value

        _, column_group = function_group.token_next_by(
            i=token_groups.Parenthesis, idx=func_idx
        )
        _, column_identifiers = column_group.token_next_by(
            i=(token_groups.IdentifierList, token_groups.Identifier)
        )
        _, column_names, _ = self._parse_identifiers(column_identifiers)

        idx, value_group = statement.token_next_by(i=token_groups.Values, idx=idx)
        _, parenthesis_group = value_group.token_next_by(i=token_groups.Parenthesis)
        value_identifiers = parenthesis_group.flatten()

        values = [
            value
            for value in value_identifiers
            if not value.ttype == token_types.Punctuation and not value.is_whitespace
        ]

        assert len(column_names) == len(
            values
        ), f"Lengths didn't match:\ncolumns: {column_names}\nvalues: {values}"

        record = {col: extract_value(val) for col, val in zip(column_names, values)}

        collection = self._client.query(q.get(q.collection(table_name)))
        field_metadata = collection["data"].get("metadata", {}).get("fields")
        cleaned_record = {}

        if field_metadata is not None:
            for field_name, field_constraints in field_metadata.items():
                field_value = (
                    field_constraints.get("default")
                    if record.get(field_name) is None
                    else record.get(field_name)
                )

                cleaned_record[field_name] = field_value

        try:
            result = self._client.query(
                q.create(q.collection(table_name), {"data": cleaned_record})
            )
        except fauna_errors.BadRequest as err:
            if "document is not unique" not in str(err):
                raise err

            unique_field_names = [
                field_name
                for field_name, field_constraints in field_metadata.items()
                if field_constraints.get("unique")
            ]
            raise exceptions.ProgrammingError(
                "Tried to create a document with duplicate value for a unique field.\n"
                f"Document:\n\t{record}"
                f"Unique fields:\n\t{unique_field_names}"
            )

        return [self._fauna_data_to_dict(result)]

    def _execute_delete(self, statement: token_groups.Statement) -> SQLResult:
        _, table = statement.token_next_by(i=token_groups.Identifier)

        comparisons = self._extract_where_conditions(statement)
        records_to_delete = self._matched_records(table.value, comparisons)

        results = self._client.query(
            q.delete(q.select("ref", q.get(records_to_delete)))
        )

        return [self._clean_fauna_key_values(results["data"])]

    def _execute_update(self, statement: token_groups.Statement) -> SQLResult:
        idx, table_identifier = statement.token_next_by(i=token_groups.Identifier)
        table_name = table_identifier.value

        idx, _ = statement.token_next_by(m=(token_types.Keyword, "SET"), idx=idx)
        idx, comparison_group = statement.token_next_by(
            i=token_groups.Comparison, idx=idx
        )
        _, update_column = comparison_group.token_next_by(i=token_groups.Identifier)
        idx, comparison = comparison_group.token_next_by(
            m=(token_types.Comparison, "=")
        )
        update_column_value = update_column.value

        if comparison is None:
            raise exceptions.NotSupportedError()

        _, update_value = comparison_group.token_next(idx, skip_ws=True)
        update_value_value = extract_value(update_value)

        comparisons = self._extract_where_conditions(statement)
        records_to_update = self._matched_records(table_name, comparisons)

        # Can't figure out how to return updated record count as part of an update call
        update_count = self._client.query(
            q.count(records_to_update),
        )

        self._client.query(
            q.update(
                q.select(
                    "ref",
                    q.get(records_to_update),
                ),
                {"data": {update_column_value: update_value_value}},
            )
        )

        return [{"count": update_count}]

    def _extract_where_conditions(self, statement) -> Optional[Comparisons]:
        _, where_group = statement.token_next_by(i=token_groups.Where)

        if where_group is None:
            return None

        _, or_keyword = where_group.token_next_by(m=(token_types.Keyword, "OR"))

        if or_keyword is not None:
            raise exceptions.NotSupportedError("OR not yet supported in WHERE clauses.")

        comparisons: Comparisons = {"by_id": None, "by_index": []}
        condition_idx = 0

        while True:
            _, and_keyword = where_group.token_next_by(m=(token_types.Keyword, "AND"))
            should_have_and_keyword = condition_idx > 0
            condition_idx, condition = where_group.token_next_by(
                i=token_groups.Comparison, idx=condition_idx
            )

            if condition is None:
                break

            assert not should_have_and_keyword or (
                should_have_and_keyword and and_keyword is not None
            )

            _, column = condition.token_next_by(i=token_groups.Identifier)
            # Assumes column has form <table_name>.<column_name>
            condition_column = column.tokens[-1]

            _, equals = condition.token_next_by(m=(token_types.Comparison, "="))
            if equals is None:
                raise exceptions.NotSupportedError(
                    "Only column-value equality conditions are currently supported"
                )

            _, condition_check = condition.token_next_by(t=token_types.Literal)
            condition_value = extract_value(condition_check)

            column_name = str(condition_column.value)

            if column_name == "id":
                assert not isinstance(condition_value, (float, datetime))
                comparisons["by_id"] = condition_value
            else:
                comparisons["by_index"].append((column_name, condition_value))

        return comparisons

    def _matched_records(
        self, collection_name: str, comparisons: Optional[Comparisons]
    ):
        if comparisons is None:
            return q.intersection(q.match(q.index(f"all_{collection_name}")))

        matched_records = []

        if comparisons["by_id"] is not None:
            if any(comparisons["by_index"]):
                raise exceptions.NotSupportedError(
                    "When querying by ID, including other conditions in the WHERE "
                    "clause is not supported."
                )

            return q.ref(q.collection(collection_name), comparisons["by_id"])

        for comparison_field, comparison_value in comparisons["by_index"]:
            matched_records.append(
                q.match(
                    q.index(f"{collection_name}_by_{comparison_field}"),
                    comparison_value,
                )
            )

        return q.intersection(*matched_records)

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
        if column_names[0] == "*":
            return document

        return {key: value for key, value in document.items() if key in column_names}
