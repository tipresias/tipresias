"""Module for all FaunaDB functionality."""

from typing import Literal, Union, Any, Dict, Optional
import os
import json
import logging

import requests
from django.conf import settings
from gql import gql, Client, AIOHTTPTransport

ImportMode = Union[Literal["merge"], Literal["overwrite"]]

FAUNADB_DOMAIN = (
    "https://graphql.fauna.com"
    if settings.ENVIRONMENT == "production"
    else "http://faunadb:8084"
)


class FaunadbClient:
    """API client for calling FaunaDB endpoints."""

    @classmethod
    def import_schema(cls, mode: ImportMode = "merge"):
        """Import a GQL schema.

        Params:
        -------
        mode: how to update the GQL schema. Accepts "merge" to update existing schema
            or "overwrite" to replace it.
        """
        url = f"{FAUNADB_DOMAIN}/import?mode={mode}"
        schema_filepath = os.path.join(settings.BASE_DIR, "server/db/schema.gql")

        with open(schema_filepath, "rb") as f:
            schema_file = f.read()

        requests.post(
            url,
            data=schema_file,
            params={"mode": mode},
            headers={
                "Authorization": f"Bearer {settings.FAUNADB_KEY}",
                "X-Schema-Preview": "partial-update-mutation",
            },
        )

    @classmethod
    def graphql(
        cls, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a GraphQL query to a FaunaDB endpoint.

        Params:
        -------
        query: GraphQL query string
        """
        transport = AIOHTTPTransport(
            url=f"{FAUNADB_DOMAIN}/graphql",
            headers={
                "Authorization": f"Bearer {settings.FAUNADB_KEY}",
                "X-Schema-Preview": "partial-update-mutation",
            },
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
