"""Translate a ALTER SQL query into an equivalent FQL query."""

import typing

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import models, common


def _fetch_column_info_refs(table_name: str, column_name: str):
    return q.intersection(
        q.match(
            q.index(
                common.index_name(
                    "information_schema_columns_",
                    column_name="table_name_",
                    index_type=common.IndexType.TERM,
                )
            ),
            table_name,
        ),
        q.join(
            q.range(
                q.match(
                    q.index(
                        common.index_name(
                            "information_schema_columns_",
                            column_name="name_",
                            index_type=common.IndexType.VALUE,
                        )
                    ),
                ),
                [column_name],
                [column_name],
            ),
            q.lambda_(
                ["value", "ref"],
                q.match(
                    q.index(
                        common.index_name(
                            "information_schema_columns_",
                            index_type=common.IndexType.REF,
                        )
                    ),
                    q.var("ref"),
                ),
            ),
        ),
    )


def _translate_drop_default(table_name: str, column_name: str) -> QueryExpression:
    drop_default = q.map_(
        q.lambda_(
            "column_info_ref",
            q.update(q.var("column_info_ref"), {"data": {"default_": None}}),
        ),
        q.paginate(_fetch_column_info_refs(table_name, column_name)),
    )

    return q.let(
        {
            "altered_docs": drop_default,
            # Should only be one document that matches the unique combination
            # of collection and field name, so we just select the first.
            "altered_ref": q.select([0, "ref"], q.var("altered_docs")),
        },
        {"data": [{"id": q.var("altered_ref")}]},
    )


def _translate_alter_column(
    statement: token_groups.Statement,
    table: models.Table,
    starting_idx: int,
) -> QueryExpression:
    idx, column_identifier = statement.token_next_by(
        i=token_groups.Identifier, idx=starting_idx
    )
    column = models.Column.from_identifier(column_identifier)
    table.add_column(column)

    _, drop = statement.token_next_by(m=(token_types.DDL, "DROP"), idx=idx)
    _, default = statement.token_next_by(m=(token_types.Keyword, "DEFAULT"))

    if drop and default:
        return _translate_drop_default(table.name, table.columns[0].name)

    raise exceptions.NotSupportedError(
        "For statements with ALTER COLUMN, only DROP DEFAULT is currently supported."
    )


def translate_alter(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate an ALTER SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    idx, table_keyword = statement.token_next_by(m=(token_types.Keyword, "TABLE"))
    assert table_keyword is not None

    idx, table_identifier = statement.token_next_by(i=token_groups.Identifier, idx=idx)
    table = models.Table.from_identifier(table_identifier)

    _, second_alter = statement.token_next_by(m=(token_types.DDL, "ALTER"), idx=idx)
    _, column_keyword = statement.token_next_by(
        m=(token_types.Keyword, "COLUMN"), idx=idx
    )

    if second_alter and column_keyword:
        return [_translate_alter_column(statement, table, idx)]

    raise exceptions.NotSupportedError(
        "For ALTER TABLE queries, only ALTER COLUMN is currently supported."
    )
