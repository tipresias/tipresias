"""Module for all FaunaDB functionality."""

from typing import Union, Any, Dict, List, Optional, Tuple, cast, Sequence
from time import sleep

from faunadb.client import FaunaClient
from faunadb import query as q, errors as fauna_errors
from faunadb.objects import Ref
import sqlparse
from sqlparse import tokens as token_types
from sqlparse import sql as token_groups

SQLResult = List[Dict[str, Any]]


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
        sql_statements = sqlparse.parse(query)

        assert len(sql_statements) <= 1, (
            "Only one SQL statement at a time is currently supported. "
            f"The following query has two:\n{query}"
        )

        sql_statement = sql_statements[0]
        return self._execute_sql_statement(sql_statement)

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

        raise FaunaClientError(f"Unsupported SQL statement received:\n{statement}")

    def _execute_select(self, statement: token_groups.Statement) -> SQLResult:
        _, table_name_token = statement.token_next_by(
            m=(token_types.Keyword, "TABLE_NAME")
        )

        if table_name_token is not None:
            results = self._client.query(
                q.map_(
                    q.lambda_("collection", q.get(q.var("collection"))),
                    q.paginate(q.collections()),
                )
            )

            return [self._fauna_data_to_dict(result) for result in results["data"]]

        _, identifiers = statement.token_next_by(
            i=(token_groups.Identifier, token_groups.IdentifierList)
        )

        assert (
            "INFORMATION_SCHEMA" not in identifiers.value
        ), f"{statement}\n is not yet supported."

        table_names, column_names, alias_names = self._parse_identifiers(identifiers)

        # We can only handle one table at a time for now
        assert len(set(table_names)) == 1
        table_name = table_names[0]

        result = self._client.query(
            q.map_(
                q.lambda_("document", q.get(q.var("document"))),
                q.paginate(q.match(q.index(f"all_{table_name}"))),
            ),
        )

        column_alias_map = {
            column: alias
            for column, alias in zip(column_names, alias_names)
            if alias is not None
        }
        return [
            self._fauna_data_to_dict(data, alias_map=column_alias_map)
            for data in result["data"]
        ]

    def _execute_create(self, statement: token_groups.Statement) -> SQLResult:
        idx, table_keyword = statement.token_next_by(m=(token_types.Keyword, "TABLE"))
        assert table_keyword is not None

        idx, table_identifier = statement.token_next_by(
            i=token_groups.Identifier, idx=idx
        )
        table_name = table_identifier.value
        assert table_name is not None

        result = self._create_collection(table_name, 0)
        collection = result["ref"]

        self._client.query(
            q.create_index({"name": f"all_{table_name}", "source": collection})
        )

        return [self._fauna_ref_to_dict(result["ref"])]

    def _execute_drop(self, statement: token_groups.Statement) -> SQLResult:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "TABLE"))
        _, table_identifier = statement.token_next_by(
            i=token_groups.Identifier, idx=idx
        )

        table_name = table_identifier.value
        assert table_name is not None

        result = self._client.query(q.delete(q.collection(table_name)))
        return [self._fauna_ref_to_dict(result["ref"])]

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

        result = self._client.query(
            q.create(q.collection(table_name), {"data": record})
        )
        return [self._fauna_data_to_dict(result)]

    def _execute_delete(self, statement: token_groups.Statement) -> SQLResult:
        idx, table = statement.token_next_by(i=token_groups.Identifier)
        _, where = statement.token_next_by(idx=idx, i=token_groups.Where)
        # Only works for one condition for now.
        _, condition = where.token_next_by(i=token_groups.Comparison)
        assert condition is not None, str(statement)

        # Only works for column-based conditions for now.
        cond_idx, column = condition.token_next_by(i=token_groups.Identifier)
        assert column is not None, str(statement)

        # Assumes column has form <table_name>.<column_name>
        condition_column = column.tokens[-1]

        # Only works for column value equality for now
        cond_idx, equals = condition.token_next_by(
            cond_idx, m=(token_types.Comparison, "=")
        )
        assert equals is not None, str(statement)

        cond_idx, condition_check = condition.token_next(
            cond_idx, skip_ws=True, skip_cm=True
        )
        # We check the idx to make sure a condition_check was found
        assert cond_idx is not None, str(statement)

        condition_value = self._extract_value(condition_check)

        records_to_delete = (
            q.ref(q.collection(table.value), condition_value)
            if condition_column.value == "id"
            else q.select(
                "ref",
                q.get(
                    q.match(
                        q.index(f"{table.value}_by_{condition_column.value}"),
                        condition_value,
                    )
                ),
            )
        )
        results = self._client.query(q.delete(records_to_delete))

        return [results["data"]]

    def _create_collection(self, collection_name: str, retries: int):
        # Sometimes Fauna needs time to do something when trying to create collections,
        # so we retry with gradual backoff. This seems to only be an issue when
        # creating/deleting collections in quick succession, so might not matter
        # in production where that happens less frequently.
        try:
            return self._client.query(q.create_collection({"name": collection_name}))
        except fauna_errors.BadRequest as err:
            if "document data is not valid" not in str(err) or retries >= 10:
                raise err

            sleep(retries)
            return self._create_collection(collection_name, retries + 1)

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

        tok_idx, next_token = identifier.token_next(idx, skip_ws=True, skip_cm=True)
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
    def _extract_value(token: token_groups.Token) -> Union[str, int, float]:
        value = token.value
        if isinstance(value, str):
            return value.replace("'", "")

        return value

    @staticmethod
    def _fauna_ref_to_dict(ref: Ref) -> Dict[str, Any]:
        ref_dict = {}

        for key, value in ref.value.items():
            if isinstance(value, Ref):
                ref_dict[f"{key}_id"] = value.id()
            else:
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
