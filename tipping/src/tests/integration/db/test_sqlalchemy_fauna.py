# pylint: disable=missing-docstring

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, inspect


def test_db_connection(fauna_engine):
    fauna_engine.connect()


def test_create_table(fauna_engine):
    table_name = "users"
    Base = declarative_base()

    class User(Base):  # pylint: disable=unused-variable
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        name = Column(String(250), nullable=False)
        date_joined = Column(DateTime(), nullable=False)
        age = Column(Integer())

    Base.metadata.create_all(fauna_engine)
    Base.metadata.reflect(fauna_engine)

    # It creates the table
    assert table_name in fauna_engine.table_names()


def test_drop_table(fauna_engine):
    table_name = "users"
    Base = declarative_base()

    class User(Base):  # pylint: disable=unused-variable
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        name = Column(String(250), nullable=False)
        date_joined = Column(DateTime(), nullable=False)
        age = Column(Integer())

    Base.metadata.create_all(fauna_engine)
    Base.metadata.reflect(fauna_engine)

    User.__table__.drop(fauna_engine)
    Base.metadata.reflect(fauna_engine)

    inspector = inspect(fauna_engine)

    # It drops the table
    assert table_name not in fauna_engine.table_names()
    # It drops all associated indexes
    assert not any(inspector.get_indexes(table_name))
