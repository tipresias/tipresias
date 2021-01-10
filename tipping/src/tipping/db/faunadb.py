"""Module for all FaunaDB functionality."""

from typing import Literal, Union, Any, Dict, List, Iterable, Optional

from faunadb.client import FaunaClient
from faunadb import query as q
from faunadb.objects import Ref
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, Name


ImportMode = Union[Literal["merge"], Literal["override"]]
SQLResult = List[Dict[str, Any]]


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
        result = self._execute_sql_statement(sql_statement)
        return [self._fauna_ref_to_dict(ref) for ref in result]

    def _execute_sql_statement(self, statement: Statement) -> List[Ref]:
        tokens = [
            sql_token for sql_token in statement.tokens if not sql_token.is_whitespace
        ]

        if f"{tokens[0]} {tokens[1]}".upper() == "SELECT TABLE_NAME":
            collections = self._client.query(q.paginate(q.collections()))
            return collections["data"]

        if f"{tokens[0]} {tokens[1]}" == "CREATE TABLE":
            table_name = tokens[2].get_name()

            self._client.query(q.create_collection({"name": table_name}))

            # Fauna is document-based, so doesn't define fields on table creation.
            # So, we just need the primary key to create an index for finding documents
            # by pk.
            primary_key = self._extract_primary_key(tokens)
            if primary_key is not None:
                self._client.query(
                    q.create_index(
                        {
                            "name": f"{table_name}_by_{primary_key}",
                            "source": q.collection(table_name),
                            "terms": [{"field": ["data", "deptno"]}],
                            "unique": True,
                        }
                    )
                )

        return []

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

    @staticmethod
    def _fauna_ref_to_dict(ref: Ref) -> Dict[str, Any]:
        ref_dict = {}

        for key, value in ref.value.items():
            if isinstance(value, Ref):
                ref_dict[f"{key}_id"] = value.id()
            else:
                ref_dict[key] = value

        return ref_dict
