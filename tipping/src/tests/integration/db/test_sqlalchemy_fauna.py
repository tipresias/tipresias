# pylint: disable=missing-docstring

from sqlalchemy.engine import create_engine


def test_db_connection(fauna_secret):
    engine = create_engine(f"fauna://faunadb:8443/?secret={fauna_secret}")
    engine.connect()
