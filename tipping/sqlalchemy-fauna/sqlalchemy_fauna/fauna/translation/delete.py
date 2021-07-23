"""Translate a drop SQL query into an equivalent FQL query."""

import typing

from sqlparse import sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from .common import parse_where
from . import models


def translate_delete(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate a DELETE SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    sql_query = models.SQLQuery.from_statement(statement)
    table = sql_query.tables[0]

    _, where_group = statement.token_next_by(i=(token_groups.Where))
    records_to_delete = parse_where(where_group, table)
    delete_records = q.delete(q.select("ref", q.get(records_to_delete)))

    return [
        q.let(
            {"response": q.select("data", delete_records)},
            {"data": [q.var("response")]},
        )
    ]
