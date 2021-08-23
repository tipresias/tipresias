# pylint: disable=missing-docstring,redefined-outer-name

from datetime import datetime, timezone
import functools

from sqlalchemy import inspect, exc as sqlalchemy_exceptions, sql
import pytest
from faker import Faker
import numpy as np

from tests.fixtures.models import Child, User


Fake = Faker()


def test_create_index(fauna_engine, user_columns):
    expected_index_columns = [col for col in user_columns if col != "id"]
    inspector = inspect(fauna_engine)
    indexes = inspector.get_indexes("users")
    name_index = None

    for index in indexes:
        if index["name"] == "users_by_name_value":
            name_index = index
            break

    assert name_index is not None
    assert set(name_index["column_names"]) == set(expected_index_columns)


def test_drop_table(fauna_engine):
    User.__table__.drop(fauna_engine)
    inspector = inspect(fauna_engine)

    # It drops the table
    with fauna_engine.connect() as connection:
        assert not fauna_engine.has_table(connection, "users")
    # It drops all associated indexes
    assert not any(inspector.get_indexes("users"))


def test_insert_record(fauna_session):
    account_credit = Fake.pyfloat()
    age = 30
    date_joined = Fake.date_time_this_year(tzinfo=timezone.utc)

    user = User(
        name="Bob", date_joined=date_joined, age=age, account_credit=account_credit
    )
    fauna_session.add(user)
    fauna_session.commit()

    users = fauna_session.execute(sql.select(User)).scalars().all()

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


def test_select_empty_table(fauna_session):
    user_records = fauna_session.execute(sql.select(User.id, User.name)).scalars().all()
    assert len(user_records) == 0


def test_select_all_records(fauna_session):
    names = ["Bob", "Linda", "Tina"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    user_records = fauna_session.execute(sql.select(User)).scalars().all()

    # It fetches the records
    assert len(users) == len(user_records)


def test_select_by_field_equality(fauna_session):
    filter_name = "Bob"
    names = [filter_name, "Linda", "Tina"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    user_records = (
        fauna_session.execute(sql.select(User).where(User.name == filter_name))
        .scalars()
        .all()
    )

    # It fetches the records
    assert len(user_records) == 1
    assert user_records[0].name == filter_name


# Numpy ints & floats aren't instances of Python's native int or float,
# so we need to perform extra checks to account for them.
@pytest.mark.parametrize("filter_age", [40, np.int16(40)])
def test_select_by_numeric_field_comparison(filter_age, fauna_session):
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

    # For '=' comparison
    user_records = (
        fauna_session.execute(sql.select(User).where(User.age == filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 2
    for user_record in user_records:
        assert user_record.age == filter_age

    # For '>' comparison
    user_records = (
        fauna_session.execute(sql.select(User).where(User.age > filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 1
    for user_record in user_records:
        assert user_record.age > filter_age

    # For '>=' comparison
    user_records = (
        fauna_session.execute(sql.select(User).where(User.age >= filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 3
    for user_record in user_records:
        assert user_record.age >= filter_age

    # For '<' comparison
    user_records = (
        fauna_session.execute(sql.select(User).where(User.age < filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 2
    for user_record in user_records:
        assert user_record.age < filter_age

    # For '<=' comparison
    user_records = (
        fauna_session.execute(sql.select(User).where(User.age <= filter_age))
        .scalars()
        .all()
    )

    assert len(user_records) == 4
    for user_record in user_records:
        assert user_record.age <= filter_age


def test_delete_record_conditionally(fauna_session):
    names = ["Bob", "Linda"]
    users = [User(name=name, date_joined=datetime.now(), age=30) for name in names]
    for user in users:
        fauna_session.add(user)
    fauna_session.commit()

    user_to_delete = users[0]
    fauna_session.execute(sql.delete(User).where(User.id == user_to_delete.id))
    fauna_session.commit()
    user_names = fauna_session.execute(sql.select(User.name)).scalars().all()

    # It deletes the record
    assert "Linda" in user_names
    assert user_to_delete.name not in user_names


def test_unique_constraint(fauna_session):
    fauna_session.add(User(name="Bob", date_joined=datetime.now(), age=30))
    fauna_session.add(User(name="Bob", date_joined=datetime.now(), age=60))

    with pytest.raises(
        sqlalchemy_exceptions.ProgrammingError,
        match="Tried to create a document with duplicate value for a unique field",
    ):
        fauna_session.commit()


def test_relationships(fauna_session):
    fauna_session.add(User(name="Bob"))
    fauna_session.commit()

    user = (
        fauna_session.execute(sql.select(User).where(User.name == "Bob"))
        .scalars()
        .first()
    )

    fauna_session.add(Child(name="Tina", user_id=user.id))
    fauna_session.add(Child(name="Gene", user_id=user.id))
    fauna_session.add(Child(name="Louise", user_id=user.id))
    fauna_session.commit()

    assert len(user.children) == 3


def test_insert_with_null_foreign_key(fauna_session):
    name = Fake.first_name()
    fauna_session.add(Child(name=name))
    fauna_session.commit()

    child = (
        fauna_session.execute(sql.select(Child).where(Child.name == name))
        .scalars()
        .first()
    )
    assert child.id is not None
    assert child.user_id is None


def test_count(fauna_session):
    assert fauna_session.execute(sql.select(sql.func.count(User.id))).scalar() == 0

    names = ["Bob", "Linda", "Louise"]

    for name in names:
        fauna_session.add(User(name=name))

    fauna_session.commit()

    assert fauna_session.execute(sql.select(sql.func.count(User.id))).scalar() == len(
        names
    )


def test_count_with_empty_results(fauna_session):
    assert fauna_session.execute(sql.select(sql.func.count(User.id))).scalar() == 0

    names = ["Bob", "Linda", "Louise"]

    for name in names:
        fauna_session.add(User(name=name))

    fauna_session.commit()

    user_count = fauna_session.execute(
        sql.select(sql.func.count(User.id)).where(User.name == "No one")
    ).scalar()

    assert user_count == 0


def test_select_distinct(fauna_session):
    user_attributes = [("Bob", 40), ("Linda", 40), ("Louise", 12)]

    for name, age in user_attributes:
        fauna_session.add(User(name=name, age=age))

    distinct_ages = (
        fauna_session.execute(sql.select(User.age).distinct()).scalars().all()
    )

    assert len(distinct_ages) == 2
    assert set(distinct_ages) == set([40, 12])


def test_select_is_null(fauna_session):
    user_attributes = [("Bob", "Cook"), ("Linda", "Waitress"), ("Louise", None)]

    for name, job in user_attributes:
        fauna_session.add(User(name=name, job=job))

    queried_users = (
        fauna_session.execute(
            sql.select(User).where(
                User.job == None  # pylint: disable=singleton-comparison
            )
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 1
    assert queried_users[0].job is None


def test_join(fauna_session):
    users = [
        ("Bob", ["Louise", "Tina", "Gene"]),
        ("Jimmy", ["Jimmy Jr.", "Ollie", "Andy"]),
    ]

    for user_name, names in users:
        user = User(name=user_name)
        fauna_session.add(user)

        for name in names:
            child = Child(name=name, user=user)
            fauna_session.add(child)

    users = (
        fauna_session.execute(
            sql.select(User, Child).join(User.children).where(Child.name == "Louise")
        )
        .scalars()
        .all()
    )

    assert len(users) == 1
    queried_user = users[0]
    assert queried_user.name == "Bob"


def test_order_by(fauna_session):
    names = ["Zoe", "Anne", "Mary", "Diana", "Tina"]
    for name in names:
        fauna_session.add(User(name=name))

    fauna_session.commit()

    users = fauna_session.execute(sql.select(User).order_by(User.name)).scalars().all()
    user_names = [user.name for user in users]
    assert user_names == sorted(names)

    users = (
        fauna_session.execute(sql.select(User).order_by(User.name.desc()))
        .scalars()
        .all()
    )
    user_names = [user.name for user in users]
    assert user_names == list(reversed(sorted(names)))


def test_join_order_by(fauna_session):
    users = [
        ("Bob", ["Louise", "Tina", "Gene"]),
        ("Jimmy", ["Jimmy Jr.", "Ollie", "Andy"]),
    ]

    for user_name, names in users:
        user = User(name=user_name)
        fauna_session.add(user)

        for name in names:
            child = Child(name=name, user=user)
            fauna_session.add(child)

    children = (
        fauna_session.execute(
            sql.select(Child, User).join(Child.user).order_by(Child.name)
        )
        .scalars()
        .all()
    )

    names = functools.reduce(
        lambda agg_names, curr_names: agg_names + curr_names[1], users, []
    )
    assert [child.name for child in children] == sorted(names)


def test_limit(fauna_session):
    limit = 2
    user_names = [Fake.first_name() for _ in range(5)]

    for name in user_names:
        fauna_session.add(User(name=name))

    fauna_session.commit()

    users = fauna_session.execute(sql.select(User).limit(limit)).scalars().all()
    queried_user_names = [user.name for user in users]

    assert queried_user_names == user_names[:limit]


def test_update(fauna_session):
    user = User(name=Fake.first_name(), age=Fake.pyint())
    fauna_session.add(user)
    fauna_session.commit()

    new_name = Fake.first_name()
    user.name = new_name
    new_age = Fake.pyint()
    user.age = new_age
    fauna_session.commit()

    queried_user = fauna_session.execute(sql.select(User)).scalars().first()

    assert queried_user.name == new_name
    assert queried_user.age == new_age


def test_multiple_update(fauna_session):
    user_count = 5
    users = [User(name=Fake.first_name(), age=Fake.pyint()) for _ in range(user_count)]

    for user in users:
        fauna_session.add(user)

    fauna_session.commit()

    new_names = []
    for user in users:
        new_name = Fake.first_name()
        user.name = new_name
        new_names.append(new_name)

    fauna_session.commit()

    queried_users = fauna_session.execute(sql.select(User)).scalars().all()
    for user in queried_users:
        assert user.name in new_names
