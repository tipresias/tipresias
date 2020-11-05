"""Test helpers for FaunaDB functionality."""

from tipping.db.faunadb import FaunadbClient


def reset_faunadb(client: FaunadbClient):
    """Reset the test DB."""
    client.import_schema(mode="overwrite")
