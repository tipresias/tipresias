"""Translate a UPDATE SQL query into an equivalent FQL query."""

import typing

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from .common import extract_value, parse_where
from .models import SQLQuery


def translate_update(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate a UPDATE SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    sql_query = SQLQuery.from_statement(statement)
    table = sql_query.tables[0]

    idx, comparison_group = statement.token_next_by(i=token_groups.Comparison)
    idx, comparison = comparison_group.token_next_by(m=(token_types.Comparison, "="))

    if comparison is None:
        raise exceptions.ProgrammingError("No '=' were found for value assignment.")

    _, update_value = comparison_group.token_next(idx, skip_ws=True)
    update_value_value = extract_value(update_value)

    _, where_group = statement.token_next_by(i=token_groups.Where)
    records_to_update = parse_where(where_group, table)

    updated_count = q.do(
        q.update(
            q.select(
                "ref",
                q.get(records_to_update),
            ),
            {"data": {table.columns[0].name: update_value_value}},
        ),
        # Can't figure out how to return updated record count as part of an update call
        q.count(records_to_update),
    )

    return [q.let({"count": updated_count}, {"data": [{"count": q.var("count")}]})]
