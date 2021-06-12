"""Translate a drop SQL query into an equivalent FQL query."""

from sqlparse import sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from .common import parse_where


def translate_delete(statement: token_groups.Statement) -> QueryExpression:
    """Translate a DELETE SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    idx, table = statement.token_next_by(i=token_groups.Identifier)
    _, where_group = statement.token_next_by(i=(token_groups.Where), idx=idx)

    records_to_delete = parse_where(where_group, table.value)

    return q.delete(q.select("ref", q.get(records_to_delete)))
