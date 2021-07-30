"""Parse WHERE clauses to generate comparable FQL queries."""

import typing

from sqlparse import tokens as token_types, sql as token_groups
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions
from . import models, common


def _parse_is_null(
    where_group: token_groups.Where,
    table: models.Table,
    starting_idx: typing.Optional[int],
) -> QueryExpression:
    idx = starting_idx or 0
    idx, comparison_identifier = where_group.token_next_by(
        i=token_groups.Identifier, idx=idx
    )
    columns = models.Column.from_identifier_group(comparison_identifier)
    assert len(columns) == 1
    table.add_column(columns[0])
    field_name = columns[0].name

    idx, is_keyword = where_group.token_next(idx, skip_ws=True, skip_cm=True)
    idx, null_keyword = where_group.token_next(idx, skip_ws=True, skip_cm=True)

    assert (
        is_keyword
        and is_keyword.value == "IS"
        and null_keyword
        and null_keyword.value == "NULL"
    )

    convert_to_ref_set = lambda index_match: q.join(
        index_match,
        q.lambda_(
            ["value", "ref"],
            q.match(q.index(f"{table.name}_by_ref_terms"), q.var("ref")),
        ),
    )
    comparison_value = None
    equality_range = q.range(
        q.match(q.index(f"{table.name}_by_{field_name}")),
        [comparison_value],
        [comparison_value],
    )

    return q.if_(
        q.exists(q.index(f"{table.name}_by_{field_name}_terms")),
        q.match(
            q.index(f"{table.name}_by_{field_name}_terms"),
            comparison_value,
        ),
        convert_to_ref_set(equality_range),
    )


def _parse_comparison(
    comparison_group: token_groups.Comparison, table: models.Table
) -> QueryExpression:
    _, comparison_identifier = comparison_group.token_next_by(i=token_groups.Identifier)
    columns = models.Column.from_identifier_group(comparison_identifier)
    assert len(columns) == 1
    table.add_column(columns[0])
    field_name = columns[0].name

    comp_idx, comparison = comparison_group.token_next_by(t=token_types.Comparison)
    value_idx, comparison_check = comparison_group.token_next_by(t=token_types.Literal)

    if comparison_check is None:
        raise exceptions.NotSupportedError(
            "Only single, literal values are permitted for comparisons "
            "in WHERE clauses."
        )
    comparison_value = common.extract_value(comparison_check)

    convert_to_ref_set = lambda index_match: q.join(
        index_match,
        q.lambda_(
            ["value", "ref"],
            q.match(q.index(f"{table.name}_by_ref_terms"), q.var("ref")),
        ),
    )

    get_collection_fields = lambda name: q.select(
        [common.DATA, "metadata", "fields"], q.get(q.collection(name))
    )

    equality_range = q.range(
        q.match(q.index(f"{table.name}_by_{field_name}")),
        [comparison_value],
        [comparison_value],
    )

    if comparison.value == "=":
        if field_name == "ref":
            assert isinstance(comparison_value, str)
            return q.singleton(q.ref(q.collection(table.name), comparison_value))

        return q.let(
            {
                "ref_index": q.index(f"{table.name}_by_{field_name}_refs"),
                "term_index": q.index(f"{table.name}_by_{field_name}_terms"),
                "references": q.select(
                    [field_name, "references"],
                    get_collection_fields(table.name),
                    default={},
                ),
                "comparison_value": comparison_value,
            },
            q.if_(
                q.exists(q.var("ref_index")),
                q.match(
                    q.var("ref_index"),
                    common.get_foreign_key_ref(
                        q.var("comparison_value"), q.var("references")
                    ),
                ),
                q.if_(
                    q.exists(q.var("term_index")),
                    q.match(
                        q.var("term_index"),
                        comparison_value,
                    ),
                    convert_to_ref_set(equality_range),
                ),
            ),
        )

    if comparison.value in [">=", ">"]:
        field_value_greater_than_literal = value_idx > comp_idx

        if field_value_greater_than_literal:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{table.name}_by_{field_name}")),
                [comparison_value],
                [],
            )
        else:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{table.name}_by_{field_name}")),
                [],
                [comparison_value],
            )

        if comparison.value == ">=":
            return convert_to_ref_set(inclusive_comparison_range)

        return convert_to_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    if comparison.value in ["<=", "<"]:
        field_value_less_than_literal = value_idx > comp_idx

        if field_value_less_than_literal:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{table.name}_by_{field_name}")),
                [],
                [comparison_value],
            )
        else:
            inclusive_comparison_range = q.range(
                q.match(q.index(f"{table.name}_by_{field_name}")),
                [comparison_value],
                [],
            )

        if comparison.value == "<=":
            return convert_to_ref_set(inclusive_comparison_range)

        return convert_to_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    raise exceptions.NotSupportedError(
        "Only the following comparisons are supported in WHERE clauses: "
        "'=', '>', '>=', '<', '<='"
    )


def parse_where(
    where_group: token_groups.Where, table: models.Table
) -> QueryExpression:
    """Convert an SQL WHERE clause into an FQL match query.

    Params:
    -------
    where_group: An SQL token group representing a WHERE clause.

    Returns:
    --------
    FQL query expression that matches on the same conditions as the WHERE clause.
    """
    if where_group is None:
        return q.intersection(q.match(q.index(f"all_{table.name}")))

    _, or_keyword = where_group.token_next_by(m=(token_types.Keyword, "OR"))
    if or_keyword is not None:
        raise exceptions.NotSupportedError("OR not yet supported in WHERE clauses.")

    _, between_keyword = where_group.token_next_by(m=(token_types.Keyword, "BETWEEN"))
    if between_keyword is not None:
        raise exceptions.NotSupportedError(
            "BETWEEN not yet supported in WHERE clauses."
        )

    comparisons = []
    comparison_idx = 0

    while True:
        and_idx, and_keyword = where_group.token_next_by(
            m=(token_types.Keyword, "AND"), idx=comparison_idx
        )
        should_have_and_keyword = comparison_idx > 0
        comparison_idx, comparison = where_group.token_next_by(
            m=(token_types.Keyword, "IS"), i=token_groups.Comparison, idx=comparison_idx
        )

        if comparison is None:
            break

        assert not should_have_and_keyword or (
            should_have_and_keyword and and_keyword is not None
        )

        comparison_query = (
            _parse_is_null(where_group, table, and_idx)
            if comparison.value == "IS"
            else _parse_comparison(comparison, table)
        )
        comparisons.append(comparison_query)

    return q.intersection(*comparisons)
