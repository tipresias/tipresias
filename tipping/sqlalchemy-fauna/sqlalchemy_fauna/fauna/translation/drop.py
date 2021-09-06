"""Translate a DROP SQL query into an equivalent FQL query."""

import typing

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from . import common


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
    table_name = table_identifier.value

    deleted_collection = q.select("ref", q.delete(q.collection(table_name)))
    return [
        q.do(
            q.map_(
                q.lambda_("ref", q.delete(q.var("ref"))),
                q.paginate(
                    q.union(
                        q.match(
                            q.index(
                                common.index_name(
                                    "information_schema_tables_",
                                    column_name="name_",
                                    index_type=common.IndexType.TERM,
                                )
                            )
                        ),
                        q.join(
                            q.range(
                                q.match(
                                    q.index(
                                        common.index_name(
                                            "information_schema_columns_",
                                            column_name="table_name_",
                                            index_type=common.IndexType.VALUE,
                                        )
                                    )
                                ),
                                [table_name],
                                [table_name],
                            ),
                            q.lambda_(
                                ["value", "ref"],
                                q.match(
                                    common.index_name(
                                        "information_schema_columns_",
                                        index_type=common.IndexType.REF,
                                    ),
                                    q.var("ref"),
                                ),
                            ),
                        ),
                        q.join(
                            q.range(
                                q.match(
                                    q.index(
                                        common.index_name(
                                            "information_schema_indexes_",
                                            column_name="table_name_",
                                            index_type=common.IndexType.VALUE,
                                        )
                                    )
                                ),
                                [table_name],
                                [table_name],
                            ),
                            q.lambda_(
                                ["value", "ref"],
                                q.match(
                                    common.index_name(
                                        "information_schema_indexes_",
                                        index_type=common.IndexType.REF,
                                    ),
                                    q.var("ref"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            q.let(
                {"collection": deleted_collection},
                {"data": [{"id": q.var("collection")}]},
            ),
        )
    ]
