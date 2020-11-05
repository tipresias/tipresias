# pylint: disable=missing-docstring


def test_import_schema_success(faunadb_client):
    faunadb_client.import_schema()
