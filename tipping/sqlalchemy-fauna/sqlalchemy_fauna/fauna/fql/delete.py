"""Translate a drop SQL query into an equivalent FQL query."""

import typing

from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import sql
from . import common


def translate_delete(sql_query: sql.SQLQuery) -> typing.List[QueryExpression]:
    """Translate a DELETE SQL query into an equivalent FQL query.

    Params:
    -------
    sql_query: An SQLQuery instance.

    Returns:
    --------
    An FQL query expression.
    """
    table = sql_query.tables[0]
    filter_group = (
        None if not any(sql_query.filter_groups) else sql_query.filter_groups[0]
    )

    records_to_delete = common.define_document_set(table, filter_group)
    delete_records = q.delete(q.select("ref", q.get(records_to_delete)))

    return q.let(
        {"response": q.select("data", delete_records)},
        {"data": [q.var("response")]},
    )
