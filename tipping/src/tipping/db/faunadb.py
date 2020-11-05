"""Module for all FaunaDB functionality."""

from typing import Literal, Union, Any, Dict, Optional
import os
import json
import logging

import requests
from gql import gql, Client, AIOHTTPTransport

from tipping import settings

ImportMode = Union[Literal["merge"], Literal["overwrite"]]

FAUNADB_DOMAIN = (
    "https://graphql.fauna.com"
    if settings.ENVIRONMENT == "production"
    else "http://faunadb:8084"
)


class FaunadbClient:
    """API client for calling FaunaDB endpoints."""

    def __init__(self, faunadb_key=None):
        """
        Params:
        -------
        faunadb_key: API key to use to access a FaunaDB database.
        """
        self.faunadb_key = faunadb_key or settings.FAUNADB_KEY

    def import_schema(self, mode: ImportMode = "merge"):
        """Import a GQL schema.

        Params:
        -------
        mode: how to update the GQL schema. Accepts "merge" to update existing schema
            or "overwrite" to replace it.
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
            raise err

        errors = result.get("errors", [])

        if any(errors):
            logging.error(graphql_variables)
            raise Exception(json.dumps(errors, indent=2))

        return result

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.faunadb_key}",
            "X-Schema-Preview": "partial-update-mutation",
        }
