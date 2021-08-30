# pylint: disable=missing-docstring,redefined-outer-name

from datetime import timezone
import functools

from sqlalchemy import inspect, exc as sqlalchemy_exceptions, sql
import pytest
from faker import Faker
import numpy as np
from tests.fixtures.factories import UserFactory

from tests.fixtures import models, factories


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
    models.User.__table__.drop(fauna_engine)
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

    user = models.User(
        name="Bob", date_joined=date_joined, age=age, account_credit=account_credit
    )
    fauna_session.add(user)
    fauna_session.commit()

    users = fauna_session.execute(sql.select(models.User)).scalars().all()

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
    user_records = (
        fauna_session.execute(sql.select(models.User.id, models.User.name))
        .scalars()
        .all()
    )
    assert len(user_records) == 0


def test_select_all_records(fauna_session):
    user_count = 3

    for _ in range(user_count):
        factories.UserFactory()

    queried_users = fauna_session.execute(sql.select(models.User)).scalars().all()

    assert len(queried_users) == user_count


def test_select_by_field_equality(fauna_session):
    filter_name = "Bob Belcher"
    names = [Fake.first_name() for _ in range(3)] + [filter_name]

    for name in names:
        factories.UserFactory(name=name)

    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(models.User.name == filter_name)
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 1
    assert queried_users[0].name == filter_name


# Numpy ints & floats aren't instances of Python's native int or float,
# so we need to perform extra checks to account for them.
@pytest.mark.parametrize("filter_age", [40, np.int16(40)])
def test_select_by_numeric_field_comparison(filter_age, fauna_session):
    queried_age = int(filter_age)
    ages = [
        45,
        queried_age,
        queried_age,
        14,
        10,
    ]

    for age in ages:
        UserFactory(age=age)

    # For '=' comparison
    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(models.User.age == filter_age)
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 2
    for user_record in queried_users:
        assert user_record.age == filter_age

    # For '>' comparison
    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(models.User.age > filter_age)
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 1
    for user_record in queried_users:
        assert user_record.age > filter_age

    # For '>=' comparison
    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(models.User.age >= filter_age)
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 3
    for user_record in queried_users:
        assert user_record.age >= filter_age

    # For '<' comparison
    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(models.User.age < filter_age)
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 2
    for user_record in queried_users:
        assert user_record.age < filter_age

    # For '<=' comparison
    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(models.User.age <= filter_age)
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 4
    for user_record in queried_users:
        assert user_record.age <= filter_age


def test_delete_record_conditionally(fauna_session):
    names = ["Bob", "Linda"]
    users = [factories.UserFactory(name=name) for name in names]
    fauna_session.commit()

    user_to_delete, user_to_keep = users
    fauna_session.execute(
        sql.delete(models.User).where(models.User.id == user_to_delete.id)
    )
    fauna_session.commit()

    queried_names = fauna_session.execute(sql.select(models.User.name)).scalars().all()

    assert user_to_keep.name in queried_names
    assert user_to_delete.name not in queried_names


def test_unique_constraint(fauna_session):
    name = "Bob"
    factories.UserFactory(name=name)

    duplicate_user = models.User(name=name, date_joined=Fake.date_this_decade())
    fauna_session.add(duplicate_user)

    with pytest.raises(
        sqlalchemy_exceptions.ProgrammingError,
        match="Tried to create a document with duplicate value for a unique field",
    ):
        fauna_session.commit()


def test_relationships(fauna_session):
    user = factories.UserFactory()

    fauna_session.add(models.Child(name="Tina", user=user))
    fauna_session.add(models.Child(name="Gene", user=user))
    fauna_session.add(models.Child(name="Louise", user=user))
    fauna_session.commit()

    assert len(user.children) == 3


def test_insert_with_null_foreign_key(fauna_session):
    child = models.Child(name=Fake.first_name())
    fauna_session.add(child)
    fauna_session.commit()

    assert child.id is not None
    assert child.user_id is None


def test_count(fauna_session):
    user_count = 3
    count_result = fauna_session.execute(
        sql.select(sql.func.count(models.User.id))
    ).scalar()

    assert count_result == 0

    for _ in range(user_count):
        factories.UserFactory()

    count_result = fauna_session.execute(
        sql.select(sql.func.count(models.User.id))
    ).scalar()
    assert count_result == user_count


def test_count_with_empty_results(fauna_session):
    nonexistent_name = "No one"

    assert (
        fauna_session.execute(sql.select(sql.func.count(models.User.id))).scalar() == 0
    )

    for _ in range(3):
        factories.UserFactory()

    empty_user_count = fauna_session.execute(
        sql.select(sql.func.count(models.User.id)).where(
            models.User.name == nonexistent_name
        )
    ).scalar()

    assert empty_user_count == 0


def test_select_distinct(fauna_session):
    ages = [40, 40, 12]

    for age in ages:
        factories.UserFactory(age=age)

    distinct_ages = (
        fauna_session.execute(sql.select(models.User.age).distinct()).scalars().all()
    )

    assert set(distinct_ages) == set(ages)


def test_select_is_null(fauna_session):
    jobs = ["Cook", "Waitress", None]

    for job in jobs:
        factories.UserFactory(job=job)

    queried_users = (
        fauna_session.execute(
            sql.select(models.User).where(
                models.User.job == None  # pylint: disable=singleton-comparison
            )
        )
        .scalars()
        .all()
    )

    assert len(queried_users) == 1
    assert queried_users[0].job is None


def test_join(fauna_session):
    names = [
        ("Bob", ["Louise", "Tina", "Gene"]),
        ("Jimmy", ["Jimmy Jr.", "Ollie", "Andy"]),
    ]

    for user_name, child_names in names:

        user = factories.UserFactory(name=user_name)

        for child_name in child_names:
            factories.ChildFactory(name=child_name, user=user)

    users = (
        fauna_session.execute(
            sql.select(models.User, models.Child)
            .join(models.User.children)
            .where(models.Child.name == "Louise")
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
        factories.UserFactory(name=name)

    queried_users = (
        fauna_session.execute(sql.select(models.User).order_by(models.User.name))
        .scalars()
        .all()
    )
    user_names = [user.name for user in queried_users]
    assert user_names == sorted(names)

    queried_users = (
        fauna_session.execute(sql.select(models.User).order_by(models.User.name.desc()))
        .scalars()
        .all()
    )
    user_names = [user.name for user in queried_users]
    assert user_names == list(reversed(sorted(names)))


def test_join_order_by(fauna_session):
    names = [
        ("Bob", ["Louise", "Tina", "Gene"]),
        ("Jimmy", ["Jimmy Jr.", "Ollie", "Andy"]),
    ]

    for user_name, child_names in names:

        user = factories.UserFactory(name=user_name)

        for child_name in child_names:
            factories.ChildFactory(name=child_name, user=user)

    queried_children = (
        fauna_session.execute(
            sql.select(models.Child, models.User)
            .join(models.Child.user)
            .order_by(models.Child.name)
        )
        .scalars()
        .all()
    )

    child_names = functools.reduce(
        lambda agg_names, curr_names: agg_names + curr_names[1], names, []
    )
    assert [child.name for child in queried_children] == sorted(child_names)


def test_limit(fauna_session):
    limit = 2
    user_names = [Fake.first_name() for _ in range(limit * 2)]

    for name in user_names:
        factories.UserFactory(name=name)

    queried_users = (
        fauna_session.execute(sql.select(models.User).limit(limit)).scalars().all()
    )
    queried_user_names = [user.name for user in queried_users]

    assert queried_user_names == user_names[:limit]


def test_update(fauna_session):
    user = factories.UserFactory()

    new_name = Fake.first_name()
    user.name = new_name
    new_age = Fake.pyint()
    user.age = new_age
    fauna_session.commit()

    queried_user = fauna_session.execute(sql.select(models.User)).scalars().first()

    assert queried_user.name == new_name
    assert queried_user.age == new_age


def test_multiple_update(fauna_session):
    user_count = 5
    users = [factories.UserFactory() for _ in range(user_count)]

    new_names = []
    for idx, user in enumerate(users):
        new_name = f"{Fake.first_name()}{idx}"
        user.name = new_name
        new_names.append(new_name)

    fauna_session.commit()

    queried_users = fauna_session.execute(sql.select(models.User)).scalars().all()
    for user in queried_users:
        assert user.name in new_names
