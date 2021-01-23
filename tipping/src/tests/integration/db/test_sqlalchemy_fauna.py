# pylint: disable=missing-docstring,redefined-outer-name

from datetime import datetime
import itertools

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, inspect
from sqlalchemy.orm import sessionmaker
import pytest

from tipping.db.sqlalchemy_fauna import dialect


@pytest.fixture()
def user_model():
    table_name = "users"
    Base = declarative_base()

    class User(Base):  # pylint: disable=unused-variable
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        date_joined = Column(DateTime, nullable=False)
        age = Column(Integer)
        finger_count = Column(Integer, default=10)

    return User, Base


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

    # It creates the table
    with fauna_engine.connect() as connection:
        assert dialect.FaunaDialect().has_table(connection, table_name)


def test_drop_table(fauna_engine, user_model):
    User, Base = user_model
    table_name = User.__tablename__

    Base.metadata.create_all(fauna_engine)

    User.__table__.drop(fauna_engine)
    inspector = inspect(fauna_engine)

    # It drops the table
    with fauna_engine.connect() as connection:
        assert not fauna_engine.has_table(connection, table_name)
    # It drops all associated indexes
    assert not any(inspector.get_indexes(table_name))


def test_insert_record(fauna_engine, user_model):
    User, Base = user_model
    Base.metadata.create_all(fauna_engine)

    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    user = User(name="Bob", date_joined=datetime.now(), age=30)
    session.add(user)
    session.commit()

    users = session.query(User).all()

    # It creates the record
    assert len(users) == 1
    assert user.name == "Bob"


def test_select_all_records(fauna_engine, user_model):
    User, Base = user_model
    Base.metadata.create_all(fauna_engine)

    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    names = ["Bob", "Linda", "Tina"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        session.add(user)
    session.commit()

    user_records = session.query(User).all()

    # It fetches the records
    assert len(users) == len(user_records)


def test_delete_record_conditionally(fauna_engine, user_model):
    User, Base = user_model
    Base.metadata.create_all(fauna_engine)

    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    names = ["Bob", "Linda"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        session.add(user)
    session.commit()

    user_to_delete = users[0]
    session.query(User).filter(User.id == user_to_delete.id).delete()
    session.commit()
    user_names = list(
        itertools.chain.from_iterable(
            session.query(User).with_entities(User.name).all()
        )
    )

    # It deletes the record
    assert "Linda" in user_names
    assert user_to_delete.name not in user_names
