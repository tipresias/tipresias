# pylint: disable=missing-docstring,redefined-outer-name

from sqlalchemy_fauna.fauna import translation


def test_format_sql_query():
    sql_query = (
        "SELECT users.id, users.name, users.date_joined, users.age, users.finger_count "
        "FROM users"
    )
    expected_sql_string = (
        "SELECT users.id,\n"
        "       users.name,\n"
        "       users.date_joined,\n"
        "       users.age,\n"
        "       users.finger_count\n"
        "FROM users"
    )

    assert translation.format_sql_query(sql_query) == expected_sql_string
