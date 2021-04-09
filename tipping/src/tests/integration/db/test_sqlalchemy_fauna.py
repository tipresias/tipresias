# pylint: disable=missing-docstring,redefined-outer-name

from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    inspect,
    exc as sqlalchemy_exceptions,
    select,
    delete,
)
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

    users = session.execute(select(User)).scalars().all()

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

    user_records = session.execute(select(User)).scalars().all()

    # It fetches the records
    assert len(users) == len(user_records)


def test_select_by_unique_field(fauna_engine, user_model):
    User, Base = user_model
    Base.metadata.create_all(fauna_engine)

    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    filter_name = "Bob"
    names = [filter_name, "Linda", "Tina"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        session.add(user)
    session.commit()

    user_records = (
        session.execute(select(User).where(User.name == filter_name)).scalars().all()
    )

    # It fetches the records
    assert len(user_records) == 1
    assert user_records[0].name == filter_name


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
    session.execute(delete(User).where(User.id == user_to_delete.id))
    session.commit()
    user_names = session.execute(select(User.name)).scalars().all()

    # It deletes the record
    assert "Linda" in user_names
    assert user_to_delete.name not in user_names


def test_unique_constraint(fauna_engine, user_model):
    User, Base = user_model
    Base.metadata.create_all(fauna_engine)

    DBSession = sessionmaker(bind=fauna_engine)
    session = DBSession()

    session.add(User(name="Bob", date_joined=datetime.now(), age=30))
    session.add(User(name="Bob", date_joined=datetime.now(), age=60))

    with pytest.raises(
        sqlalchemy_exceptions.ProgrammingError,
        match="Tried to create a document with duplicate value for a unique field",
    ):
        session.commit()
