# pylint: disable=missing-docstring,redefined-outer-name

import sqlparse
from sqlparse import sql as token_groups, tokens as token_types
import pytest
from faker import Faker

from sqlalchemy_fauna.sql import sql_table
from sqlalchemy_fauna import exceptions

from ...fixtures.factories import ColumnFactory, ComparisonFactory


Fake = Faker()


class TestColumn:
    column_name = "name"

    @pytest.mark.parametrize(
        ["column_sql", "expected_table_name", "expected_alias"],
        [
            (f"users.{column_name}", "users", column_name),
            (column_name, None, column_name),
            (f"users.{column_name} AS user_name", "users", "user_name"),
        ],
    )
    def test_from_identifier(self, column_sql, expected_table_name, expected_alias):
        sql_query = f"SELECT {column_sql} FROM users"
        statement = sqlparse.parse(sql_query)[0]
        _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

        column = sql_table.Column.from_identifier(column_identifier)

        assert column.name == self.column_name
        assert column.table_name == expected_table_name
        assert column.alias == expected_alias
        assert column.position == 0

    @staticmethod
    @pytest.mark.parametrize(
        ["column_sql", "expected_name", "expected_function"],
        [
            (
                f"count(users.{column_name})",
                f"count(users.{column_name})",
                sql_table.Function.COUNT,
            ),
        ],
    )
    def test_from_function_identifier(column_sql, expected_name, expected_function):
        sql_string = f"SELECT {column_sql} FROM users"
        statement = sqlparse.parse(sql_string)[0]
        _, column_function = statement.token_next_by(i=(token_groups.Function))

        column = sql_table.Column.from_identifier(
            token_groups.Identifier([column_function]), 0
        )

        assert column.name == expected_name
        assert column.function_name == expected_function.value
        assert column.position == 0

    @pytest.mark.parametrize(
        ["column_sql_string", "error_message"],
        [("SUM(users.id) AS sum_1", "SUM"), ("AVG(users.id) AS avg_1", "AVG")],
    )
    def test_unsupported_from_identifier(self, column_sql_string, error_message):
        sql_string = f"SELECT {column_sql_string} FROM users"
        statement = sqlparse.parse(sql_string)[0]
        _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

        with pytest.raises(exceptions.NotSupportedError, match=error_message):
            sql_table.Column.from_identifier(column_identifier)

    @staticmethod
    def test_from_comparison_group():
        sql_string = "UPDATE users SET users.name = 'Bob'"
        statement = sqlparse.parse(sql_string)[0]
        _, comparison_group = statement.token_next_by(i=token_groups.Comparison)

        column = sql_table.Column.from_comparison_group(comparison_group)

        assert column.name == "name"
        assert column.table_name == "users"
        assert column.value == "Bob"
        assert column.position == 0

    @staticmethod
    def test_unsupported_from_comparison_group():
        sql_string = "UPDATE users SET users.name = users.occupation"
        statement = sqlparse.parse(sql_string)[0]
        _, comparison_group = statement.token_next_by(i=token_groups.Comparison)

        with pytest.raises(
            exceptions.NotSupportedError,
            match="Only updating to literal values is currently supported",
        ):
            sql_table.Column.from_comparison_group(comparison_group)

    @staticmethod
    def test_column():
        column = ColumnFactory(
            position=0, table_name="users", name="name", alias="alias"
        )
        assert str(column) == "name"
        assert column.alias_map == {column.name: column.alias}

        table = sql_table.Table(name="users", columns=[column])
        column.table = table
        assert column.table_name == table.name

    table_name = "users"
    select_single_column = f"SELECT {table_name}.id FROM {table_name}"
    select_columns = f"SELECT {table_name}.id, {table_name}.name FROM {table_name}"
    select_aliases = (
        f"SELECT {table_name}.id AS user_id, {table_name}.name AS user_name "
        "FROM {table_name}"
    )
    select_function = f"SELECT count({table_name}.id) FROM {table_name}"
    select_function_alias = (
        f"SELECT count({table_name}.id) AS count_{table_name} FROM {table_name}"
    )
    insert = "INSERT INTO users (name, age, finger_count) VALUES ('Bob', 30, 10)"

    @staticmethod
    @pytest.mark.parametrize(
        ["sql_query", "expected_columns", "expected_aliases"],
        [
            (select_single_column, ["ref"], ["id"]),
            (select_columns, ["ref", "name"], ["id", "name"]),
            (select_aliases, ["ref", "name"], ["user_id", "user_name"]),
            (select_function, [f"count({table_name}.id)"], [f"count({table_name}.id)"]),
            (
                select_function_alias,
                [f"count({table_name}.id)"],
                [f"count_{table_name}"],
            ),
            (insert, ["name", "age", "finger_count"], ["name", "age", "finger_count"]),
        ],
    )
    def test_from_identifier_group(sql_query, expected_columns, expected_aliases):
        statement = sqlparse.parse(sql_query)[0]
        _, identifiers = statement.token_next_by(
            i=(
                token_groups.Identifier,
                token_groups.IdentifierList,
                token_groups.Function,
            )
        )

        columns = sql_table.Column.from_identifier_group(identifiers)

        for column in columns:
            assert column.name in expected_columns
            assert column.alias in expected_aliases


class TestTable:
    @staticmethod
    def test_table():
        table_name = "users"
        sql_query = f"SELECT users.name FROM {table_name} WHERE users.name = 'Bob'"
        statement = sqlparse.parse(sql_query)[0]
        _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))
        _, where_group = statement.token_next_by(i=(token_groups.Where))

        column = sql_table.Column.from_identifier(column_identifier)
        sql_filter_groups = sql_table.FilterGroup.from_where_group(where_group)
        sql_filters = sql_filter_groups[0].filters
        table = sql_table.Table(name=table_name, columns=[column], filters=sql_filters)
        assert table.name == table_name
        assert str(table) == table_name

        assert len(table.columns) == 1
        assert table.columns[0].name == column.name
        assert table.alias_map == {table.name: {column.name: column.alias}}

        assert len(table.filters) == 1
        assert table.filters[0].value == sql_filters[0].value

    @staticmethod
    @pytest.mark.parametrize(
        ["table_name", "sql_string"],
        [
            ["users", "SELECT users.name FROM users"],
            ["users", "SELECT users.name FROM users AS users_1"],
        ],
    )
    def test_table_from_identifier(table_name, sql_string):
        statement = sqlparse.parse(sql_string)[0]
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
        _, table_identifier = statement.token_next_by(
            i=(token_groups.Identifier), idx=idx
        )

        table = sql_table.Table.from_identifier(table_identifier)
        assert table.name == table_name

    @staticmethod
    def test_add_column():
        table_name = "users"
        sql_query = f"SELECT users.name FROM {table_name}"
        statement = sqlparse.parse(sql_query)[0]
        _, column_identifier = statement.token_next_by(i=(token_groups.Identifier))

        column = sql_table.Column.from_identifier(column_identifier)
        table = sql_table.Table(name=table_name)

        table.add_column(column)

        assert table.columns == [column]

    @staticmethod
    def test_add_filter():
        table_name = "users"
        sql_query = f"SELECT users.name FROM {table_name} WHERE users.age > 30"
        statement = sqlparse.parse(sql_query)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))

        sql_filter_groups = sql_table.FilterGroup.from_where_group(where_group)
        sql_filters = sql_filter_groups[0].filters
        table = sql_table.Table(name=table_name)

        table.add_filter(sql_filters[0])

        assert table.filters == sql_filters

    @staticmethod
    def test_add_join():
        table_name = "users"
        foreign_table_name = "accounts"
        sql_query = (
            f"SELECT {table_name}.name, {foreign_table_name}.amount "
            f"FROM {table_name} JOIN {foreign_table_name} "
            f"ON {table_name}.id = {foreign_table_name}.user_id"
        )
        statement = sqlparse.parse(sql_query)[0]
        _, comparison_group = statement.token_next_by(i=(token_groups.Comparison))

        table = sql_table.Table(name=table_name)
        foreign_table = sql_table.Table(name=foreign_table_name)

        table.add_join(foreign_table, comparison_group, sql_table.JoinDirection.RIGHT)

        assert table.right_join_table == foreign_table
        assert table.right_join_key.name == "ref"
        assert foreign_table.left_join_table == table
        assert foreign_table.left_join_key.name == "user_id"

    @staticmethod
    def test_invalid_add_join():
        table_name = "users"
        foreign_table_name = "accounts"
        sql_query = (
            f"SELECT {table_name}.name, {foreign_table_name}.amount "
            f"FROM {table_name} JOIN {foreign_table_name} "
            f"ON {table_name}.name = {foreign_table_name}.user_name"
        )
        statement = sqlparse.parse(sql_query)[0]
        _, comparison_group = statement.token_next_by(i=(token_groups.Comparison))

        table = sql_table.Table(name=table_name)
        foreign_table = sql_table.Table(name=foreign_table_name)

        with pytest.raises(
            exceptions.NotSupportedError, match="Table joins are only permitted on IDs"
        ):
            table.add_join(
                foreign_table, comparison_group, sql_table.JoinDirection.RIGHT
            )


class TestComparison:
    select_values = "SELECT * FROM users"

    @staticmethod
    @pytest.mark.parametrize(
        ["sql_string", "expected_operator"],
        [
            (
                select_values + f" WHERE users.{Fake.word()} = '{Fake.word()}'",
                sql_table.ComparisonOperator.EQUAL,
            ),
            (
                select_values + f" WHERE users.{Fake.word()} > {Fake.pyint()}",
                sql_table.ComparisonOperator.GREATER_THAN,
            ),
            (
                select_values + f" WHERE {Fake.pyint()} > users.{Fake.word()}",
                sql_table.ComparisonOperator.LESS_THAN,
            ),
        ],
    )
    def test_from_comparison_group(sql_string, expected_operator):
        statement = sqlparse.parse(sql_string)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))
        _, comparison_group = where_group.token_next_by(i=token_groups.Comparison)

        comparison = sql_table.Comparison.from_comparison_group(comparison_group)

        assert comparison.operator == expected_operator

    @staticmethod
    @pytest.mark.parametrize(
        "sql_string",
        [
            select_values + f" WHERE users.{Fake.word()} IN ({Fake.word()})",
            select_values + f" WHERE users.{Fake.word()} <> {Fake.pyint()}",
            select_values + f" WHERE users.{Fake.word()} != {Fake.pyint()}",
        ],
    )
    def test_invalid_from_comparison_group(sql_string):
        statement = sqlparse.parse(sql_string)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))
        _, comparison_group = where_group.token_next_by(i=token_groups.Comparison)

        with pytest.raises(exceptions.NotSupportedError):
            sql_table.Comparison.from_comparison_group(comparison_group)


class TestFilter:
    @staticmethod
    def test_filter():
        column = ColumnFactory()
        comparison = ComparisonFactory
        value = "Bob"
        where_filter = sql_table.Filter(
            column=column, comparison=comparison, value=value
        )

        assert where_filter.column == column
        assert where_filter.comparison == comparison
        assert where_filter.value == value

    select_values = "SELECT * FROM users"
    id_value = Fake.credit_card_number()
    name = Fake.first_name()
    age = Fake.pyint()
    finger_count = Fake.pyint()

    @staticmethod
    @pytest.mark.parametrize(
        ["sql_string", "expected_attributes"],
        [
            # SELECT with non-ID '=' comparison
            (
                select_values + f" WHERE users.name = '{name}'",
                {
                    "comparison": ComparisonFactory(
                        operator=sql_table.ComparisonOperator.EQUAL
                    ),
                    "value": name,
                },
            ),
            # SELECT with '>' comparison
            (
                select_values + f" WHERE users.age > {age}",
                {
                    "comparison": ComparisonFactory(
                        operator=sql_table.ComparisonOperator.GREATER_THAN
                    ),
                    "value": age,
                },
            ),
            # SELECT with '>=' comparison
            (
                select_values + f" WHERE users.age >= {age}",
                {
                    "comparison": ComparisonFactory(
                        operator=sql_table.ComparisonOperator.GREATER_THAN_OR_EQUAL
                    ),
                    "value": age,
                },
            ),
            # SELECT with '<' comparison
            (
                select_values + f" WHERE users.age < {age}",
                {
                    "comparison": ComparisonFactory(
                        operator=sql_table.ComparisonOperator.LESS_THAN
                    ),
                    "value": age,
                },
            ),
            # SELECT with '<=' comparison
            (
                select_values + f" WHERE users.age <= {age}",
                {
                    "comparison": ComparisonFactory(
                        operator=sql_table.ComparisonOperator.LESS_THAN_OR_EQUAL
                    ),
                    "value": age,
                },
            ),
            # SELECT with column and comparison value in reverse order
            (
                select_values + " WHERE 'Bob' = users.name",
                {
                    "comparison": ComparisonFactory(
                        operator=sql_table.ComparisonOperator.EQUAL
                    ),
                    "value": "Bob",
                },
            ),
        ],
    )
    def test_from_comparison_group(sql_string, expected_attributes):
        statement = sqlparse.parse(sql_string)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))
        _, comparison = where_group.token_next_by(i=token_groups.Comparison)

        where_filter = sql_table.Filter.from_comparison_group(comparison)
        assert isinstance(where_filter, sql_table.Filter)
        for key, value in expected_attributes.items():
            assert getattr(where_filter, key) == value

    where_not_equal_1 = select_values + f" WHERE users.age <> {Fake.pyint()}"
    where_not_equal_2 = select_values + f" WHERE users.age != {Fake.pyint()}"
    where_like = select_values + f" WHERE users.name LIKE '%{Fake.first_name()}%'"
    where_in = (
        select_values
        + f" WHERE users.name IN ('{Fake.first_name()}', '{Fake.first_name()}')"
    )

    @staticmethod
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
            (
                where_like,
                "Only the following comparisons are supported in WHERE clauses",
            ),
            (where_in, "Only the following comparisons are supported in WHERE clauses"),
        ],
    )
    def test_unsupported_from_comparison_group(sql_query, error_message):
        statement = sqlparse.parse(sql_query)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))
        _, comparison = where_group.token_next_by(i=token_groups.Comparison)

        with pytest.raises(exceptions.NotSupportedError, match=error_message):
            sql_table.Filter.from_comparison_group(comparison)

    @staticmethod
    @pytest.mark.parametrize(
        "operator", list(sql_table.Comparison.OPERATOR_MAP.values())
    )
    def test_checks_whether_operator_methods(operator):
        comparison = ComparisonFactory(operator=operator)
        sql_filter = sql_table.Filter(
            column=ColumnFactory(), comparison=comparison, value=Fake.word()
        )

        for operator_to_compare in list(sql_table.Comparison.OPERATOR_MAP.values()):
            checks_operator = getattr(
                sql_filter, f"checks_whether_{operator_to_compare.name.lower()}"
            )

            if operator_to_compare == operator:
                assert checks_operator
            else:
                assert not checks_operator


class TestFilterGroup:
    select_values = "SELECT * FROM users"

    id_value = Fake.credit_card_number()
    name = Fake.first_name()
    age = Fake.pyint()
    finger_count = Fake.pyint()

    @staticmethod
    @pytest.mark.parametrize(
        ["sql_string", "expected_attributes"],
        [
            # SELECT *
            (
                select_values,
                [[]],
            ),
            # SELECT ID
            (
                select_values + f" WHERE users.id = '{id_value}'",
                [
                    [
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": id_value,
                        }
                    ]
                ],
            ),
            # SELECT with multiple ANDs
            (
                select_values
                + f" WHERE users.name = '{name}' AND users.age = {age} "
                + f"AND users.finger_count = {finger_count}",
                [
                    [
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": name,
                        },
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": age,
                        },
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": finger_count,
                        },
                    ]
                ],
            ),
            # SELECT with 'IS NULL' comparison
            (
                select_values + " WHERE users.job IS NULL",
                [
                    [
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": None,
                        }
                    ]
                ],
            ),
            (
                select_values + f" WHERE users.name = '{name}' OR users.age = {age}",
                [
                    [
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": name,
                        }
                    ],
                    [
                        {
                            "comparison": ComparisonFactory(
                                operator=sql_table.ComparisonOperator.EQUAL
                            ),
                            "value": age,
                        }
                    ],
                ],
            ),
        ],
    )
    def test_from_where_group(sql_string, expected_attributes):
        statement = sqlparse.parse(sql_string)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))

        filter_groups = sql_table.FilterGroup.from_where_group(where_group)
        for idx, filter_group in enumerate(filter_groups):
            for sql_filter, expected_filter_attributes in zip(
                filter_group.filters, expected_attributes[idx]
            ):
                assert isinstance(sql_filter, sql_table.Filter)
                for key, value in expected_filter_attributes.items():
                    assert getattr(sql_filter, key) == value

    where_between = (
        select_values + f" WHERE users.age BETWEEN {Fake.pyint()} AND {Fake.pyint}"
    )

    @staticmethod
    @pytest.mark.parametrize(
        ["sql_query", "error_message"],
        [
            (where_between, "BETWEEN not yet supported in WHERE clauses"),
        ],
    )
    def test_unsupported_from_where_group(sql_query, error_message):
        statement = sqlparse.parse(sql_query)[0]
        _, where_group = statement.token_next_by(i=(token_groups.Where))

        with pytest.raises(exceptions.NotSupportedError, match=error_message):
            sql_table.FilterGroup.from_where_group(where_group)
