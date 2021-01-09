# pylint: disable=missing-docstring

from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base


def test_db_connection(fauna_secret):
    Base = declarative_base()
    engine = create_engine(f"fauna://faunadb:8443/?secret={fauna_secret}")
    Base.metadata.reflect(engine)

    engine.connect()
