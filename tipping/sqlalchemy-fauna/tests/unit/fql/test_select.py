# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from faunadb.objects import _Expr as QueryExpression

from tests.fixtures.factories import (
    SQLQueryFactory,
    ColumnFactory,
    OrderByFactory,
    TableFactory,
)
from sqlalchemy_fauna.fauna.fql import select
from sqlalchemy_fauna import exceptions, sql


table = TableFactory(columns__count=2)

# These are meant to be examples of SQL queries that are not currently supported,
# but that are valid SQL and so should be supported eventually.
@pytest.mark.parametrize(
    ["sql_query", "error_message"],
    [
        (
            SQLQueryFactory(
                tables=[table],
                order_by=OrderByFactory(columns=table.columns),
            ),
            "Ordering by multiple columns is not yet supported",
        ),
    ],
)
def test_translating_unsupported_select(sql_query, error_message):
    with pytest.raises(exceptions.NotSupportedError, match=error_message):
        select.translate_select(sql_query)


@pytest.mark.parametrize(
    "sql_query",
    [
        SQLQueryFactory(table_count=1, filter_groups=[], tables__columns__alias=None),
        SQLQueryFactory(table_count=1, filter_groups=[]),
        SQLQueryFactory(
            table_count=1,
            filter_groups__filters__comparison__operator=sql.sql_table.ComparisonOperator.EQUAL,
        ),
        SQLQueryFactory(
            table_count=1,
            filter_groups=[],
            tables__columns__function_name=sql.Function.COUNT,
        ),
        SQLQueryFactory(table_count=2),
        SQLQueryFactory(table_count=1, order_by=OrderByFactory()),
        SQLQueryFactory(
            table_count=1,
            order_by=OrderByFactory(direction=sql.sql_query.OrderDirection.DESC),
        ),
        SQLQueryFactory(
            tables=[table, TableFactory(columns=[])],
            order_by=OrderByFactory(columns=table.columns[:1]),
        ),
        SQLQueryFactory(
            tables=[
                TableFactory(
                    columns=[
                        ColumnFactory(
                            function_name=sql.sql_table.Function.COUNT, table_name=None
                        )
                    ],
                    filters=[],
                ),
                TableFactory(filters__count=1, columns=[]),
            ]
        ),
    ],
)
def test_translate_select(sql_query):
    fql_query = select.translate_select(sql_query)

    assert isinstance(fql_query, QueryExpression)
