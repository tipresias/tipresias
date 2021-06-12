"""Translate a DROP SQL query into an equivalent FQL query."""

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression


def translate_drop(statement: token_groups.Statement) -> QueryExpression:
    """Translate a DROP SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "TABLE"))
    _, table_identifier = statement.token_next_by(i=token_groups.Identifier, idx=idx)

    return q.delete(q.collection(table_identifier.value))
