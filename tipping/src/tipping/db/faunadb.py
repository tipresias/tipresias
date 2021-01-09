"""Module for all FaunaDB functionality."""

from typing import Literal, Union, Any, Dict, List

from faunadb.client import FaunaClient
import sqlparse
from sqlparse.sql import Statement
from mypy_extensions import TypedDict

from tipping import settings

ImportMode = Union[Literal["merge"], Literal["override"]]
SQLResult = TypedDict("SQLResult", {"data": List[Dict[str, Any]]})


class FaunadbClient:
    """API client for calling FaunaDB endpoints."""

    def __init__(self, secret=None, scheme="http", domain="localhost", port="8443"):
        """
        Params:
        -------
        secret: API key to use to access a FaunaDB database.
        scheme: Which scheme to use when calling the database ('http' or 'https').
        domain: Domain of the database server.
        port: Port used by the database server.
        """
        secret = secret or settings.FAUNA_SECRET
        self._client = FaunaClient(
            scheme=scheme, domain=domain, port=port, secret=secret
        )

    def sql(self, query: str) -> SQLResult:
        """Convert SQL to FQL and execute the query."""
        sql_statements = sqlparse.parse(query)

        for statement in sql_statements:
            self._execute_sql_statement(statement)

        return {"data": []}

    def _execute_sql_statement(self, statement: Statement):
        for sql_token in statement.tokens:
            print(sql_token)
