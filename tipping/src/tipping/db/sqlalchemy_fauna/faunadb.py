"""Module for all FaunaDB functionality."""

from typing import Union, Any, Dict, List, Optional, Tuple, cast, Sequence
from time import sleep
import logging
from functools import reduce
from datetime import datetime
from copy import deepcopy

from faunadb.client import FaunaClient
from faunadb import query as q, errors as fauna_errors
from faunadb.objects import Ref
import sqlparse
from sqlparse import tokens as token_types
from sqlparse import sql as token_groups
from mypy_extensions import TypedDict

from . import exceptions


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


class FaunaClientError(Exception):
    """Errors raised by the FaunaClient while executing queries."""


class FaunadbClient:
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
        self._client = FaunaClient(
            scheme=scheme, domain=domain, port=port, secret=secret
        )

    def sql(self, query: str) -> SQLResult:
        """Convert SQL to FQL and execute the query."""
        formatted_query = self._format_sql(query)
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
            logging.error(formatted_query)
            raise err

    @staticmethod
    def _format_sql(sql: str) -> str:
        return sqlparse.format(
            sql, keyword_case="upper", strip_comments=True, reindent=True
        )

    def _execute_sql_statement(self, statement: token_groups.Statement) -> SQLResult:
        if statement.token_first().match(token_types.DML, "SELECT"):
            return self._execute_select(statement)

        if statement.token_first().match(token_types.DDL, "CREATE"):
            return self._execute_create(statement)

        if statement.token_first().match(token_types.DDL, "DROP"):
            return self._execute_drop(statement)

        if statement.token_first().match(token_types.DML, "INSERT"):
            return self._execute_insert(statement)

        if statement.token_first().match(token_types.DML, "DELETE"):
            return self._execute_delete(statement)

        if statement.token_first().match(token_types.DML, "UPDATE"):
            return self._execute_update(statement)

        raise exceptions.NotSupportedError()

    def _execute_select(self, statement: token_groups.Statement) -> SQLResult:
        table_name = self._extract_table_name(statement)

        if "INFORMATION_SCHEMA" in table_name:
            return self._execute_select_from_information_schema(statement)

        idx, identifiers = statement.token_next_by(
            i=(token_groups.Identifier, token_groups.IdentifierList)
        )
        table_names, column_names, alias_names = self._parse_identifiers(identifiers)

        # We can only handle one table at a time for now
        if len(set(table_names)) > 1:
            raise exceptions.NotSupportedError(
                "Only one table per query is currently supported, but received:\n",
                f"{self._format_sql(str(statement))}",
            )

        idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"), idx=idx)
        _, table_identifier = statement.token_next_by(
            i=(token_groups.Identifier), idx=idx
        )
        table_name = table_identifier.value

        condition_column, condition_value = self._extract_where_conditions(statement)

        if condition_column == "id":
            records_to_select = q.ref(q.collection(table_name), condition_value)
        elif condition_column is None:
            records_to_select = q.match(q.index(f"all_{table_name}"))
        else:
            records_to_select = q.match(
                q.index(f"{table_name}_by_{condition_column}"), condition_value
            )

        result = self._client.query(
            q.map_(
                q.lambda_("document", q.get(q.var("document"))),
                q.paginate(records_to_select),
            )
        )

        # If an index match only returns one document, the result is a dictionary,
        # otherwise, it's a dictionary wrapped in a list. Not sure why
        # (fetching by ID returns a list when paginated & mapped) and too lazy
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
                column_names, self._fauna_data_to_dict(data, alias_map=column_alias_map)
            )
            for data in result["data"]
        ]

    def _execute_create(self, statement: token_groups.Statement) -> SQLResult:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "TABLE"))

        idx, table_identifier = statement.token_next_by(
            i=token_groups.Identifier, idx=idx
        )
        table_name = table_identifier.value

        idx, column_identifiers = statement.token_next_by(
            i=token_groups.Parenthesis, idx=idx
        )

        field_metadata = self._extract_column_definitions(column_identifiers)
        result = self._create_collection(
            table_name, metadata={"metadata": {"fields": field_metadata}}
        )
        collection = result["ref"]

        self._client.query(
            q.create_index({"name": f"all_{table_name}", "source": collection})
        )

        for field_name, field_data in field_metadata.items():
            if field_name == "id" or not field_data["unique"]:
                continue

            self._client.query(
                q.create_index(
                    {
                        "name": f"{table_name}_by_{field_name}",
                        "source": collection,
                        "terms": [{"field": ["data", field_name]}],
                        "unique": True,
                    }
                )
            )

        return [self._fauna_collection_to_dict(result["ref"])]

    def _execute_drop(self, statement: token_groups.Statement) -> SQLResult:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "TABLE"))
        _, table_identifier = statement.token_next_by(
            i=token_groups.Identifier, idx=idx
        )

        result = self._client.query(q.delete(q.collection(table_identifier.value)))
        return [self._fauna_collection_to_dict(result["ref"])]

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

        record = {
            col: self._extract_value(val) for col, val in zip(column_names, values)
        }

        collection = self._client.query(q.get(q.collection(table_name)))
        field_metadata = collection["data"].get("metadata", {}).get("fields")
        cleaned_record = {}

        if field_metadata is not None:
            for field_name, field_constraints in field_metadata.items():
                field_value = record.get(field_name) or field_constraints.get("default")

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
        condition_column, condition_value = self._extract_where_conditions(statement)

        if condition_column == "id":
            records_to_delete = q.ref(q.collection(table.value), condition_value)
        elif condition_column is None:
            records_to_delete = q.match(
                q.index(f"all_{table.value}"),
            )
        else:
            records_to_delete = q.match(
                q.index(f"{table.value}_by_{condition_column}"),
                condition_value,
            )

        results = self._client.query(
            q.delete(q.select("ref", q.get(records_to_delete)))
        )

        return [results["data"]]

    def _extract_where_conditions(
        self, statement
    ) -> Tuple[Optional[str], Union[int, float, str, None]]:
        _, where_group = statement.token_next_by(i=token_groups.Where)

        if where_group is None:
            return None, None

        _, condition = where_group.token_next_by(i=token_groups.Comparison)

        idx, column = condition.token_next_by(i=token_groups.Identifier)
        # Assumes column has form <table_name>.<column_name>
        condition_column = column.tokens[-1]

        idx, equals = condition.token_next_by(idx, m=(token_types.Comparison, "="))
        if equals is None:
            raise exceptions.NotSupportedError(
                "Only column-value equality conditions are currently supported"
            )

        _, condition_check = condition.token_next(idx, skip_ws=True)
        condition_value = self._extract_value(condition_check)

        return str(condition_column.value), condition_value

    def _execute_select_from_information_schema(
        self, statement: token_groups.Statement
    ) -> SQLResult:
        _, select_keyword = statement.token_next_by(
            m=[
                (token_types.Keyword, "TABLE_NAME"),
                (token_types.Keyword, "COLUMN_NAME"),
            ]
        )

        if "TABLE_NAME" in select_keyword.value:
            result = self._client.query(
                q.map_(
                    q.lambda_("collection", q.get(q.var("collection"))),
                    q.paginate(q.collections()),
                )
            )

            return [
                {"id": self._fauna_data_to_dict(result).get("id")}
                for result in result["data"]
            ]

        if "COLUMN_NAME" in select_keyword.value:
            # We don't use the standard logic for parsing this WHERE clause,
            # because sqlparse treats WHERE clauses in INFORMATION_SCHEMA queries
            # differently, returning flat tokens in the WHERE group
            # instead of nested token groups.
            _, where_group = statement.token_next_by(i=token_groups.Where)
            idx, condition_column = where_group.token_next_by(
                m=(token_types.Keyword, "TABLE_NAME")
            )

            if condition_column is None:
                raise exceptions.NotSupportedError(
                    "Only TABLE_NAME condition is supported for SELECT COLUMN_NAME"
                )

            idx, condition = where_group.token_next_by(
                m=(token_types.Comparison, "="), idx=idx
            )

            if condition is None:
                raise exceptions.NotSupportedError(
                    "Only column-value-based conditions (e.g. WHERE <column> = <value>) "
                    "are currently supported."
                )

            _, condition_check = where_group.token_next(idx, skip_ws=True)
            condition_value = self._extract_value(condition_check)

            result = self._client.query(q.get(q.collection(condition_value)))

            return [
                {**field_data, "name": field_name}
                for field_name, field_data in result["data"]["metadata"][
                    "fields"
                ].items()
            ]

        raise exceptions.NotSupportedError()

    @staticmethod
    def _extract_table_name(statement: token_groups.Statement) -> str:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
        _, table_identifier = statement.token_next_by(
            i=(token_groups.Identifier), idx=idx
        )
        return table_identifier.value

    def _extract_column_definitions(
        self, column_identifiers: token_groups.IdentifierList
    ) -> FieldsMetadata:
        # sqlparse doesn't group column info correctly within the Parenthesis,
        # sometimes grouping keywords/identifiers across a comma and breaking them up
        # within the same sub-clause, so we have to do some manual processing
        # to group tokens correctly.
        column_definition_groups = self._split_column_identifiers_by_comma(
            column_identifiers
        )

        return reduce(self._build_fields_metadata, column_definition_groups, {})

    @staticmethod
    def _split_column_identifiers_by_comma(
        column_identifiers: token_groups.IdentifierList,
    ) -> List[token_groups.TokenList]:
        column_tokens = list(column_identifiers.flatten())
        column_token_list = token_groups.TokenList(column_tokens)
        comma_idxs: List[Optional[int]] = [None]
        comma_idx = -1

        while True:
            if comma_idx is None:
                break

            comma_idx, _ = column_token_list.token_next_by(
                m=(token_types.Punctuation, ","), idx=comma_idx
            )

            comma_idxs.append(comma_idx)

        column_group_ranges = [
            (comma_idxs[comma_idx], comma_idxs[comma_idx + 1])
            for comma_idx in range(0, len(comma_idxs) - 1)
        ]

        return [
            token_groups.TokenList(
                column_tokens[(start if start is None else start + 1) : stop]
            )
            for start, stop in column_group_ranges
        ]

    def _build_fields_metadata(
        self,
        metadata: FieldsMetadata,
        column_definition_group: token_groups.TokenList,
    ) -> FieldsMetadata:
        return (
            self._define_primary_key(metadata, column_definition_group)
            or self._define_unique_constraint(metadata, column_definition_group)
            or self._define_column(metadata, column_definition_group)
        )

    def _define_primary_key(
        self,
        metadata: FieldsMetadata,
        column_definition_group: token_groups.TokenList,
    ) -> Optional[FieldsMetadata]:
        idx, constraint_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "CONSTRAINT")
        )

        idx, primary_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "PRIMARY"), idx=(idx or -1)
        )

        if constraint_keyword is not None and primary_keyword is None:
            raise exceptions.NotSupportedError(
                "When a column definition clause begins with CONSTRAINT, "
                "only a PRIMARY KEY constraint is supported, but the following was "
                f"recieved:\n{self._format_sql(column_definition_group)}"
            )

        if primary_keyword is None:
            return None

        # If the keyword isn't followed by column name(s), then it's part of
        # a regular column definition and should be handled by _define_column
        if not self._contains_column_name(column_definition_group, idx):
            return None

        new_metadata: FieldsMetadata = deepcopy(metadata)

        while True:
            idx, primary_key_column = column_definition_group.token_next_by(
                t=token_types.Name, idx=idx
            )

            # 'id' is defined and managed by Fauna, so we ignore any attempts
            # to manage it from SQLAlchemy
            if primary_key_column is None or primary_key_column.value == "id":
                break

            primary_key_column_name = primary_key_column.value

            new_metadata[primary_key_column_name] = {
                **DEFAULT_FIELD_METADATA,  # type: ignore
                **new_metadata.get(primary_key_column_name, {}),  # type: ignore
                "unique": True,
                "not_null": True,
            }

        return new_metadata

    def _define_unique_constraint(
        self,
        metadata: FieldsMetadata,
        column_definition_group: token_groups.TokenList,
    ) -> Optional[FieldsMetadata]:
        idx, unique_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "UNIQUE")
        )

        if unique_keyword is None:
            return None

        # If the keyword isn't followed by column name(s), then it's part of
        # a regular column definition and should be handled by _define_column
        if not self._contains_column_name(column_definition_group, idx):
            return None

        new_metadata = deepcopy(metadata)

        while True:
            idx, unique_key_column = column_definition_group.token_next_by(
                t=token_types.Name, idx=idx
            )

            # 'id' is defined and managed by Fauna, so we ignore any attempts
            # to manage it from SQLAlchemy
            if unique_key_column is None or unique_key_column.value == "id":
                break

            unique_key_column_name = unique_key_column.value

            new_metadata[unique_key_column_name] = {
                **DEFAULT_FIELD_METADATA,  # type: ignore
                **new_metadata.get(unique_key_column_name, {}),  # type: ignore
                "unique": True,
            }

        return new_metadata

    def _define_column(
        self,
        metadata: FieldsMetadata,
        column_definition_group: token_groups.TokenList,
    ) -> FieldsMetadata:
        idx, column = column_definition_group.token_next_by(t=token_types.Name)
        column_name = column.value

        if column_name == "id":
            return metadata

        idx, data_type = column_definition_group.token_next_by(
            t=token_types.Name, idx=idx
        )
        _, not_null_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "NOT NULL")
        )
        _, unique_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "UNIQUE")
        )
        _, primary_key_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "PRIMARY KEY")
        )
        _, default_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "DEFAULT")
        )
        _, check_keyword = column_definition_group.token_next_by(
            m=(token_types.Keyword, "CHECK")
        )

        if check_keyword is not None:
            raise exceptions.NotSupportedError(
                "CHECK keyword is not supported, but received:\n"
                f"{self._format_sql(column_definition_group)}"
            )

        column_metadata: Union[FieldMetadata, Dict[str, str]] = metadata.get(
            column_name, {}
        )
        is_primary_key = primary_key_keyword is not None
        is_not_null = (
            not_null_keyword is not None
            or is_primary_key
            or column_metadata.get("not_null")
            or False
        )
        is_unique = (
            unique_keyword is not None
            or is_primary_key
            or column_metadata.get("unique")
            or False
        )
        default_value = (
            default_keyword
            if default_keyword is None
            else self._extract_value(default_keyword.value)
        )

        return {
            **metadata,
            column_name: {
                **DEFAULT_FIELD_METADATA,  # type: ignore
                **metadata.get(column_name, {}),  # type: ignore
                "unique": is_unique,
                "not_null": is_not_null,
                "default": default_value,
                "type": DATA_TYPE_MAP[data_type.value],
            },
        }

    @staticmethod
    def _contains_column_name(
        token_group: Union[
            token_groups.TokenList,
            token_groups.IdentifierList,
            token_groups.Identifier,
            token_groups.Parenthesis,
        ],
        idx: int,
    ) -> bool:
        return token_group.token_next_by(t=token_types.Name, idx=idx) != (None, None)

    def _create_collection(
        self,
        collection_name: str,
        retries: int = 0,
        metadata: Optional[Union[CollectionMetadata, Dict[str, Any]]] = None,
    ):
        metadata = metadata or {}
        # Sometimes Fauna needs time to do something when trying to create collections,
        # so we retry with gradual backoff. This seems to only be an issue when
        # creating/deleting collections in quick succession, so might not matter
        # in production where that happens less frequently.
        try:
            return self._client.query(
                q.create_collection({"name": collection_name, "data": metadata})
            )
        except fauna_errors.BadRequest as err:
            if "document data is not valid" not in str(err) or retries >= 10:
                raise err

            sleep(retries)
            return self._create_collection(
                collection_name, metadata=metadata, retries=(retries + 1)
            )

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
    def _fauna_collection_to_dict(ref: Ref) -> Dict[str, Any]:
        ref_dict = {}

        for key, value in ref.value.items():
            if key == "metadata":
                continue

            if isinstance(value, Ref):
                ref_dict[f"{key}_id"] = value.id()
                continue

            ref_dict[key] = value

        return ref_dict

    @staticmethod
    def _fauna_data_to_dict(
        data: Dict[str, Any], alias_map: Dict[str, str] = None
    ) -> Dict[str, Any]:
        alias_map = alias_map or {}

        # SELECT queries usually include a nested 'data' object for the selected values,
        # but selecting TABLE_NAMES does not, and there might be other cases
        # that I haven't encountered yet.
        sub_data = data.get("data", {})
        return {
            **{"id": data["ref"].id()},
            **{
                alias_map.get(key) or key: value
                for key, value in data.items()
                if key not in ("ref", "data")
            },
            **sub_data,
        }

    def _select_columns(
        self, column_names: Sequence[str], document: Dict[str, Any]
    ) -> Dict[str, Any]:
        if column_names[0] == "*":
            return document

        return {key: value for key, value in document.items() if key in column_names}
