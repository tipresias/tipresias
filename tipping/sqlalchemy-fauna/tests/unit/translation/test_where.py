# pylint: disable=missing-docstring,redefined-outer-name

import sqlparse
from sqlparse import sql as token_groups, tokens as token_types
from faker import Faker
import pytest
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from sqlalchemy_fauna.fauna.translation import where, models

FAKE = Faker()

select_values = "SELECT * FROM users"
where_not_equal_1 = select_values + f" WHERE users.age <> {FAKE.pyint()}"
where_not_equal_2 = select_values + f" WHERE users.age != {FAKE.pyint()}"
where_between = (
    select_values + f" WHERE users.age BETWEEN {FAKE.pyint()} AND {FAKE.pyint}"
)
where_like = select_values + f" WHERE users.name LIKE '%{FAKE.first_name()}%'"
where_in = (
    select_values
    + f" WHERE users.name IN ('{FAKE.first_name()}', '{FAKE.first_name()}')"
)
where_or = (
    select_values
    + f" WHERE users.name = '{FAKE.first_name()}' OR users.age = {FAKE.pyint()}"
)


@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (
            where_not_equal_1,
            "Only the following comparisons are supported in WHERE clauses",
        ),
        (
            where_not_equal_2,
            "Only the following comparisons are supported in WHERE clauses",
        ),
        (where_between, "BETWEEN not yet supported in WHERE clauses"),
        (
            where_like,
            "Only the following comparisons are supported in WHERE clauses",
        ),
        (where_in, "Only single, literal values are permitted"),
        (where_or, "OR not yet supported in WHERE clauses."),
    ],
)
def test_parsing_unsupported_where(sql_query, error_message):
    statement = sqlparse.parse(sql_query)[0]
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)
    table = models.Table.from_identifier(table_identifier)
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        where.parse_where(where_group, table)


where_id = select_values + f" WHERE users.id = '{FAKE.credit_card_number}'"
where_equals = select_values + f" WHERE users.name = '{FAKE.first_name()}'"
where_and = (
    where_equals
    + f" AND users.age = {FAKE.pyint()} AND users.finger_count = {FAKE.pyint()}"
)
where_greater = select_values + f" WHERE users.age > {FAKE.pyint()}"
where_greater_equal = select_values + f" WHERE users.age >= {FAKE.pyint()}"
where_less = select_values + f" WHERE users.age < {FAKE.pyint()}"
where_less_equal = select_values + f" WHERE users.age <= {FAKE.pyint()}"
where_is_null = select_values + " WHERE users.job IS NULL"


@pytest.mark.parametrize(
    "sql_query",
    [
        select_values,
        where_id,
        where_equals,
        where_and,
        where_greater,
        where_greater_equal,
        where_less,
        where_less_equal,
        where_is_null,
    ],
)
def test_parsing_where(sql_query):
    statement = sqlparse.parse(sql_query)[0]
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)
    table = models.Table.from_identifier(table_identifier)
    _, where_group = statement.token_next_by(i=(token_groups.Where))

    fql_query = where.parse_where(where_group, table)
    assert isinstance(fql_query, QueryExpression)
