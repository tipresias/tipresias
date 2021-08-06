"""Parse WHERE clauses to generate comparable FQL queries."""

from functools import partial
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions
from . import models, common


def _define_match_set(query_filter: models.Filter) -> QueryExpression:
    field_name = query_filter.column.name
    comparison_value = query_filter.value
    index_name_for_collection = partial(common.index_name, query_filter.table_name)

    convert_to_ref_set = lambda index_match: q.join(
        index_match,
        q.lambda_(
            ["value", "ref"],
            q.match(
                q.index(index_name_for_collection(index_type=common.IndexType.REF)),
                q.var("ref"),
            ),
        ),
    )

    get_collection_fields = lambda name: q.select(
        [common.DATA, "metadata", "fields"], q.get(q.collection(name))
    )

    index_name_for_field = partial(index_name_for_collection, field_name)
    equality_range = q.range(
        q.match(q.index(index_name_for_field(common.IndexType.VALUE))),
        [comparison_value],
        [comparison_value],
    )

    if query_filter.operator == "=":
        if field_name == "ref":
            assert isinstance(comparison_value, str)
            return q.singleton(
                q.ref(q.collection(query_filter.table_name), comparison_value)
            )

        return q.let(
            {
                "ref_index": q.index(
                    index_name_for_field(
                        common.IndexType.REF, foreign_key_name=field_name
                    )
                ),
                "term_index": q.index(index_name_for_field(common.IndexType.TERM)),
                "references": q.select(
                    [field_name, "references"],
                    get_collection_fields(query_filter.table_name),
                    default={},
                ),
                "comparison_value": comparison_value,
            },
            q.if_(
                q.exists(q.var("ref_index")),
                convert_to_ref_set(
                    q.match(
                        q.var("ref_index"),
                        common.get_foreign_key_ref(
                            q.var("comparison_value"), q.var("references")
                        ),
                    ),
                ),
                q.if_(
                    q.exists(q.var("term_index")),
                    q.match(
                        q.var("term_index"),
                        q.var("comparison_value"),
                    ),
                    convert_to_ref_set(equality_range),
                ),
            ),
        )

    # In the building of Filter objects from SQL tokens, we enforce the convention
    # of <column name> <operator> <value> for WHERE clauses, so we build the FQL queries
    # assuming that '>' means 'column value greater than literal value'. I can't think
    # of a good way to centralize the knowledge of this convention across
    # all query translation, so I'm leaving this note as a warning.
    if query_filter.operator in [">=", ">"]:
        inclusive_comparison_range = q.range(
            q.match(q.index(index_name_for_field(common.IndexType.VALUE))),
            [comparison_value],
            [],
        )

        if query_filter.operator == ">=":
            return convert_to_ref_set(inclusive_comparison_range)

        return convert_to_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    if query_filter.operator in ["<=", "<"]:
        inclusive_comparison_range = q.range(
            q.match(q.index(index_name_for_field(common.IndexType.VALUE))),
            [],
            [comparison_value],
        )

        if query_filter.operator == "<=":
            return convert_to_ref_set(inclusive_comparison_range)

        return convert_to_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    raise exceptions.NotSupportedError(
        f"Unsupported operator {query_filter.operator} was received."
    )


def define_document_set(table: models.Table) -> QueryExpression:
    """Build FQL match query based on filtering rules from the SQL query.

    Params:
    -------
    table: A Table object associated with a Fauna collection.

    Returns:
    --------
    FQL query expression that matches on the same conditions as the Table's filters.
    """
    filters = table.filters

    if not any(filters):
        return q.intersection(q.match(q.index(common.index_name(table.name))))

    document_sets = [_define_match_set(query_filter) for query_filter in filters]
    return q.intersection(*document_sets)
