"""Module for all FaunaDB functionality."""

from typing import Literal, Union, Any, Dict, Optional, List
import os
import logging

import requests
from gql import gql, Client, AIOHTTPTransport
from faunadb.client import FaunaClient
import sqlparse
from sqlparse.sql import Statement
from mypy_extensions import TypedDict

from tipping import settings

ImportMode = Union[Literal["merge"], Literal["override"]]
SQLResult = TypedDict("SQLResult", {"data": List[Dict[str, Any]]})

FAUNADB_DOMAIN = (
    "https://graphql.fauna.com"
    if settings.ENVIRONMENT == "production"
    else "http://faunadb:8084"
)


class GraphQLError(Exception):
    """Errors related to GraphQL queries."""


class FaunadbClient:
    """API client for calling FaunaDB endpoints."""

    def __init__(
        self, faunadb_key=None, scheme="http", domain="localhost", port="8443"
    ):
        """
        Params:
        -------
        faunadb_key: API key to use to access a FaunaDB database.
        """
        self.faunadb_key = faunadb_key or settings.FAUNADB_KEY
        self._client = FaunaClient(
            scheme=scheme, domain=domain, port=port, secret=self.faunadb_key
        )

    def import_schema(self, mode: ImportMode = "merge"):
        """Import a GQL schema.

        Params:
        -------
        mode: how to update the GQL schema. Accepts "merge" to update existing schema
            or "override" to replace it.
        """
        url = f"{FAUNADB_DOMAIN}/import?mode={mode}"
        schema_filepath = os.path.join(settings.SRC_DIR, "tipping/db/schema.gql")

        with open(schema_filepath, "rb") as f:
            schema_file = f.read()

        requests.post(
            url,
            data=schema_file,
            params={"mode": mode},
            headers=self._headers,
        )

    def graphql(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a GraphQL query to a FaunaDB endpoint.

        Params:
        -------
        query: GraphQL query string
        """
        transport = AIOHTTPTransport(
            url=f"{FAUNADB_DOMAIN}/graphql",
            headers=self._headers,
        )
        graphql_client = Client(transport=transport)

        graphql_query = gql(query)
        graphql_variables = variables or {}

        try:
            result = graphql_client.execute(
                graphql_query, variable_values=graphql_variables
            )
        except Exception as err:
            logging.error(graphql_variables)
            raise GraphQLError(err) from err

        errors = result.get("errors", [])

        if any(errors):
            logging.error(graphql_variables)
            raise GraphQLError(errors)

        return result

    def sql(self, query: str) -> SQLResult:
        """Convert SQL to FQL and execute the query."""
        sql_statements = sqlparse.parse(query)

        for statement in sql_statements:
            self._execute_sql_statement(statement)

        return {"data": []}

    def _execute_sql_statement(self, statement: Statement):
        for sql_token in statement.tokens:
            print(sql_token)

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.faunadb_key}",
            "X-Schema-Preview": "partial-update-mutation",
        }
