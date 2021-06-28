# pylint: disable=missing-docstring,redefined-outer-name

from datetime import datetime, timezone

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    inspect,
    exc as sqlalchemy_exceptions,
    select,
    delete,
    func,
)
from sqlalchemy.orm import relationship
import pytest
from faker import Faker
import numpy as np

from sqlalchemy_fauna import dialect


FAKE = Faker()


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
        is_premium_member = Column(Boolean, default=False)
        account_credit = Column(Float, default=0.0)
        job = Column(String)

    return User, Base


@pytest.fixture()
def parent_child():
    Base = declarative_base()

    class Parent(Base):  # pylint: disable=unused-variable
        __tablename__ = "parents"

        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        children = relationship("Child", back_populates="parent")

    class Child(Base):  # pylint: disable=unused-variable
        __tablename__ = "children"

        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        parent_id = Column(Integer, ForeignKey("parents.id"))
        parent = relationship("Parent", back_populates="children")

    return {"parent": Parent, "child": Child, "base": Base}


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


def test_create_index(fauna_engine):
    table_name = "users"
    Base = declarative_base()

    class User(Base):  # pylint: disable=unused-variable
        __tablename__ = table_name

        id = Column(Integer, primary_key=True)
        name = Column(String(250), nullable=False, index=True)
        date_joined = Column(DateTime(), nullable=False)
        age = Column(Integer())

    Base.metadata.create_all(fauna_engine)

    inspector = inspect(fauna_engine)
    indexes = inspector.get_indexes(table_name)
    name_index = None

    for index in indexes:
        if index["name"] == "users_by_name":
            name_index = index
            break

    assert name_index is not None
    assert set(name_index["column_names"]) == set(["name", "date_joined", "age"])


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


def test_insert_record(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    account_credit = FAKE.pyfloat()
    age = 30
    date_joined = FAKE.date_time_this_year(tzinfo=timezone.utc)

    user = User(
        name="Bob", date_joined=date_joined, age=age, account_credit=account_credit
    )
    fauna_session.add(user)
    fauna_session.commit()

    users = fauna_session.execute(select(User)).scalars().all()

    # It creates the record
    assert len(users) == 1

    created_user = users[0]
    assert created_user.name == "Bob"
    assert created_user.is_premium_member is False
    assert created_user.account_credit == account_credit
    assert created_user.age == age
    assert created_user.date_joined == date_joined
    assert created_user.job is None
    assert isinstance(created_user.id, str)
    assert isinstance(int(created_user.id), int)


def test_select_empty_table(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    user_records = fauna_session.execute(select(User.id, User.name)).scalars().all()
    assert len(user_records) == 0


def test_select_all_records(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    names = ["Bob", "Linda", "Tina"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    user_records = fauna_session.execute(select(User)).scalars().all()

    # It fetches the records
    assert len(users) == len(user_records)


def test_select_by_field_equality(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    filter_name = "Bob"
    names = [filter_name, "Linda", "Tina"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    user_records = (
        fauna_session.execute(select(User).where(User.name == filter_name))
        .scalars()
        .all()
    )

    # It fetches the records
    assert len(user_records) == 1
    assert user_records[0].name == filter_name


def test_select_by_numeric_field_comparison(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    names_ages = [
        ("Teddy", 45),
        ("Bob", 40),
        ("Linda", 40),
        ("Tina", 14),
        ("Louise", 10),
    ]
    users = [
        User(name=name, date_joined=datetime.now(), age=age) for name, age in names_ages
    ]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    filter_age = 40

    # For '=' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age == filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 2
    for user_record in user_records:
        assert user_record.age == filter_age

    # For '>' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age > filter_age)).scalars().all()
    )

    assert len(user_records) == 1
    for user_record in user_records:
        assert user_record.age > filter_age

    # For '>=' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age >= filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 3
    for user_record in user_records:
        assert user_record.age >= filter_age

    # For '<' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age < filter_age)).scalars().all()
    )

    assert len(user_records) == 2
    for user_record in user_records:
        assert user_record.age < filter_age

    # For '<=' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age <= filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 4
    for user_record in user_records:
        assert user_record.age <= filter_age


def test_select_with_numpy_numeric_comparison(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    names_ages = [
        ("Teddy", 45),
        ("Bob", 40),
        ("Linda", 40),
        ("Tina", 14),
        ("Louise", 10),
    ]
    users = [
        User(name=name, date_joined=datetime.now(), age=age) for name, age in names_ages
    ]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    # Numpy ints & floats aren't instances of Python's native int or float,
    # so we need to perform extra checks to account for them.
    filter_age = np.int16(40)

    # For '=' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age == filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 2
    for user_record in user_records:
        assert user_record.age == filter_age

    # For '>' comparison
    user_records = (
        fauna_session.execute(select(User).where(User.age > filter_age)).scalars().all()
    )

    assert len(user_records) == 1
    for user_record in user_records:
        assert user_record.age > filter_age


def test_delete_record_conditionally(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    names = ["Bob", "Linda"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    user_to_delete = users[0]
    fauna_session.execute(delete(User).where(User.id == user_to_delete.id))
    fauna_session.commit()
    user_names = fauna_session.execute(select(User.name)).scalars().all()

    # It deletes the record
    assert "Linda" in user_names
    assert user_to_delete.name not in user_names


def test_unique_constraint(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    fauna_session.add(User(name="Bob", date_joined=datetime.now(), age=30))
    fauna_session.add(User(name="Bob", date_joined=datetime.now(), age=60))

    with pytest.raises(
        sqlalchemy_exceptions.ProgrammingError,
        match="Tried to create a document with duplicate value for a unique field",
    ):
        fauna_session.commit()


def test_relationships(fauna_session, parent_child):
    Base = parent_child["base"]
    Parent = parent_child["parent"]
    Child = parent_child["child"]

    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    fauna_session.add(Parent(name="Bob"))
    fauna_session.commit()

    parent = (
        fauna_session.execute(select(Parent).where(Parent.name == "Bob"))
        .scalars()
        .first()
    )

    fauna_session.add(Child(name="Tina", parent_id=parent.id))
    fauna_session.add(Child(name="Gene", parent_id=parent.id))
    fauna_session.add(Child(name="Louise", parent_id=parent.id))
    fauna_session.commit()

    assert len(parent.children) == 3


def test_count(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    assert fauna_session.execute(select(func.count(User.id))).scalar() == 0

    names = ["Bob", "Linda", "Louise"]

    for name in names:
        fauna_session.add(User(name=name))

    fauna_session.commit()

    assert fauna_session.execute(select(func.count(User.id))).scalar() == len(names)


def test_select_distinct(fauna_session, user_model):
    User, Base = user_model
    fauna_engine = fauna_session.get_bind()
    Base.metadata.create_all(fauna_engine)

    user_attributes = [("Bob", 40), ("Linda", 40), ("Louise", 12)]

    for name, age in user_attributes:
        fauna_session.add(User(name=name, age=age))

    distinct_ages = fauna_session.execute(select(User.age).distinct()).scalars().all()

    assert len(distinct_ages) == 2
    assert set(distinct_ages) == set([40, 12])
