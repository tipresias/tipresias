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
    tables = sql_query.tables

    if len(tables) > 1:
        document_set = common.join_collections(sql_query)
    else:
        document_set = common.build_document_set(sql_query.filter_group, tables[0])

    return q.map_(q.lambda_("ref", q.delete(q.var("ref"))), q.paginate(document_set))
