"""Translate a DROP SQL query into an equivalent FQL query."""

import typing

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression


def translate_drop(statement: token_groups.Statement) -> typing.List[QueryExpression]:
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

    deleted_collection = q.select("ref", q.delete(q.collection(table_identifier.value)))
    return [
        q.let(
            {"collection": deleted_collection}, {"data": [{"id": q.var("collection")}]}
        )
    ]
