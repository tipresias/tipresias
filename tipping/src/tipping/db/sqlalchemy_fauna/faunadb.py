"""Module for all FaunaDB functionality."""

from typing import Literal, Union, Any, Dict, List, Iterable, Optional
from time import sleep

from faunadb.client import FaunaClient
from faunadb import query as q, errors as fauna_errors
from faunadb.objects import Ref
import sqlparse
from sqlparse.sql import Statement, Token, Identifier, Where, Comparison
from sqlparse.tokens import Keyword, Name, DDL, DML, Punctuation
from sqlparse import tokens as token_types

ImportMode = Union[Literal["merge"], Literal["override"]]
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

    def _execute_sql_statement(self, statement: Statement) -> List[Ref]:
        tokens = [
            sql_token for sql_token in statement.tokens if not sql_token.is_whitespace
        ]

        if tokens[0].match(DML, "SELECT"):
            if tokens[1].match(Keyword, "TABLE_NAME"):
                results = self._client.query(
                    q.map_expr(
                        q.lambda_expr("x", q.get(q.var("x"))),
                        q.paginate(q.collections()),
                    )
                )
                return [self._fauna_data_to_dict(result) for result in results["data"]]

            if isinstance(tokens[1], Identifier) and tokens[2].match(Keyword, "FROM"):
                table_name = tokens[3].value
                result = self._client.query(
                    q.map_expr(
                        q.lambda_expr("x", q.get(q.var("x"))),
                        q.paginate(q.match(q.index(f"all_{table_name}"))),
                    ),
                )
                return [data["data"] for data in result["data"]]

        if tokens[0].match(DDL, "CREATE") and tokens[1].match(Keyword, "TABLE"):
            table_name = tokens[2].value

            result = self._create_collection(table_name, 0)
            collection = result["ref"]

            self._client.query(
                q.create_index({"name": f"all_{table_name}", "source": collection})
            )

            # Fauna is document-based, so doesn't define fields on table creation.
            # So, we just need the primary key to create an index for finding documents
            # by pk.
            primary_key = self._extract_primary_key(tokens)
            if primary_key is not None:
                self._client.query(
                    q.create_index(
                        {
                            "name": f"{table_name}_by_{primary_key}",
                            "source": collection,
                            "terms": [{"field": ["data", primary_key]}],
                            "unique": True,
                        }
                    )
                )

            return [self._fauna_ref_to_dict(result["ref"])]

        if tokens[0].match(DDL, "DROP") and tokens[1].match(Keyword, "TABLE"):
            table_name = tokens[2].get_name()

            result = self._client.query(q.delete(q.collection(table_name)))
            return [self._fauna_ref_to_dict(result["ref"])]

        if tokens[0].match(DML, "INSERT") and tokens[1].match(Keyword, "INTO"):
            if tokens[2].is_group:
                insert_args = [
                    sql_token
                    for sql_token in tokens[2].tokens
                    if not sql_token.is_whitespace
                ]

                table_name = insert_args[0].value
                columns = [
                    sql_token.value
                    for sql_token in insert_args[1].flatten()
                    if not sql_token.is_whitespace
                    and not sql_token.ttype == Punctuation
                ]

            if tokens[3].is_group:
                values_args = tokens[3].tokens
                values = [
                    sql_token.value.replace("'", "")
                    for sql_token in values_args[-1].flatten()
                    if not sql_token.is_whitespace
                    and not sql_token.ttype == Punctuation
                ]

            assert len(columns) == len(
                values
            ), f"Lengths didn't match:\ncolumns: {columns}\nvalues: {values}"

            record = {col: val for col, val in zip(columns, values)}
            result = self._client.query(
                q.create(q.collection(table_name), {"data": record})
            )
            return [self._fauna_ref_to_dict(result["ref"])]

        if statement.token_first().match(DML, "DELETE"):
            idx, table = statement.token_next_by(i=Identifier)
            _, where = statement.token_next_by(idx=idx, i=Where)
            # Only works for one condition for now.
            _, condition = where.token_next_by(i=Comparison)
            assert condition is not None, str(statement)

            # Only works for column-based conditions for now.
            cond_idx, column = condition.token_next_by(i=Identifier)
            assert column is not None, str(statement)

            # Assumes column has form <table_name>.<column_name>
            condition_column = column.tokens[-1]

            # Only works for column value equality for now
            cond_idx, equals = condition.token_next_by(
                cond_idx, m=(token_types.Comparison, "=")
            )
            assert equals is not None, str(statement)

            cond_idx, condition_value = condition.token_next(
                cond_idx, skip_ws=True, skip_cm=True
            )
            # We check the idx to make sure a condition_value was found
            assert cond_idx is not None, str(statement)

            results = self._client.query(
                q.delete(
                    q.select(
                        "ref",
                        q.get(
                            q.match(
                                q.index(f"{table.value}_by_{condition_column.value}"),
                                condition_value.value.replace("'", ""),
                            )
                        ),
                    )
                )
            )

            return [results["data"]]

        raise FaunaClientError(f"Unsupported SQL statement received:\n{statement}")

    def _extract_primary_key(
        self, tokens: Iterable[Token], found_primary=False
    ) -> Optional[str]:
        for token in tokens:
            if token.match(Keyword, "PRIMARY"):
                found_primary = True

            if token.match(Name, [".*"], regex=True) and found_primary:
                return token.value

            if token.is_group:
                maybe_primary_key = self._extract_primary_key(
                    token.tokens, found_primary
                )
                if maybe_primary_key is not None:
                    return maybe_primary_key

        return None

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
    def _fauna_data_to_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        ref_id = data["ref"].id()
        return {
            **{key: value for key, value in data.items() if key != "ref"},
            **{"id": ref_id},
        }
