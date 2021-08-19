"""Parse WHERE clauses to generate comparable FQL queries."""

import typing
import functools

from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions
from . import models, common


MAX_PAGE_SIZE = 100000


def _define_match_set(query_filter: models.Filter) -> QueryExpression:
    field_name = query_filter.column.name
    comparison_value = query_filter.value
    index_name_for_collection = functools.partial(
        common.index_name, query_filter.table_name
    )

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

    index_name_for_field = functools.partial(index_name_for_collection, field_name)
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
                "ref_index": q.index(index_name_for_field(common.IndexType.REF)),
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


def _build_merge(*table_names: str):
    merge = lambda agg_merge, table_name: q.merge(
        agg_merge, {table_name: q.var(f"{table_name}_data")}
    )
    return functools.reduce(merge, table_names, q.merge({}, {}))


def _build_base_page(table_name: str, inner_query: QueryExpression, order_by=None):
    if order_by is None:
        return q.select(
            "data",
            q.map_(
                q.lambda_(f"{table_name}_ref", inner_query),
                q.paginate(q.var(f"joined_{table_name}"), size=MAX_PAGE_SIZE),
            ),
        )

    ordered_result = q.join(
        q.var(f"joined_{table_name}"),
        q.index(
            common.index_name(
                table_name,
                column_name=order_by.columns[0].name,
                index_type=common.IndexType.SORT,
            )
        ),
    )
    if order_by.direction == models.OrderDirection.DESC:
        ordered_result = q.reverse(ordered_result)

    return q.select(
        "data",
        q.map_(
            q.lambda_(["_", f"{table_name}_ref"], inner_query),
            q.paginate(ordered_result, size=MAX_PAGE_SIZE),
        ),
    )


def _build_page_query(
    table: models.Table,
    merge_func: typing.Callable[[str], QueryExpression],
    order_by: typing.Optional[models.OrderBy] = None,
):
    partial_merge_func = functools.partial(merge_func, table.name)
    right_table = table.right_join_table
    left_table = table.left_join_table

    assert right_table is not None or left_table is not None, (
        "At least two tables must be included in a join query. "
        "If only querying one table, use `define_document_set` instead."
    )

    if right_table is None:
        # The inner-most page doesn't need a Union, because there aren't nested pages
        # to flatten
        inner_query = q.let(
            {
                f"{table.name}_doc": q.get(q.var(f"{table.name}_ref")),
                f"{table.name}_data": q.merge(
                    q.select("data", q.var(f"{table.name}_doc")),
                    {"ref": q.select("ref", q.var(f"{table.name}_doc"))},
                ),
            },
            partial_merge_func(),
        )
        page = _build_base_page(table.name, inner_query, order_by=order_by)
    else:
        page = q.union(
            _build_base_page(
                table.name,
                _build_page_query(right_table, partial_merge_func),
                order_by=order_by,
            )
        )

    if left_table is None:
        return q.let(
            {
                f"joined_{table.name}": define_document_set(table),
            },
            page,
        )

    left_join_key = table.left_join_key

    if left_join_key is not None and left_join_key.name == "ref":
        left_foreign_key = left_table.right_join_key
        assert left_foreign_key is not None
        return q.let(
            {
                f"{left_table.name}_doc": q.get(q.var(f"{left_table.name}_ref")),
                f"{left_table.name}_data": q.merge(
                    q.select("data", q.var(f"{left_table.name}_doc")),
                    {"ref": q.select("ref", q.var(f"{left_table.name}_doc"))},
                ),
                f"{table.name}_ref": q.select(
                    left_foreign_key.name, q.var(f"{left_table.name}_data")
                ),
                table.name: define_document_set(table),
                f"joined_{table.name}": q.intersection(
                    q.singleton(q.var(f"{table.name}_ref")), q.var(table.name)
                ),
            },
            page,
        )

    left_foreign_key = left_join_key
    assert left_foreign_key is not None
    return q.let(
        {
            f"{left_table.name}_doc": q.get(q.var(f"{left_table.name}_ref")),
            f"{left_table.name}_data": q.merge(
                q.select("data", q.var(f"{left_table.name}_doc")),
                {"ref": q.select("ref", q.var(f"{left_table.name}_doc"))},
            ),
            table.name: define_document_set(table),
            f"joined_{table.name}": q.intersection(
                q.match(
                    q.index(
                        common.index_name(
                            table.name,
                            column_name=left_foreign_key.name,
                            index_type=common.IndexType.REF,
                        )
                    ),
                    q.var(f"{left_table.name}_ref"),
                ),
                q.var(table.name),
            ),
        },
        page,
    )


def join_collections(
    left_most_table: models.Table, order_by: typing.Optional[models.OrderBy] = None
) -> QueryExpression:
    """Join together multiple collections to return their documents in the response.

    Params:
    -------
    left_most_table: The first table in a chain of JOINS

    """
    assert left_most_table.left_join_table is None
    return _build_page_query(left_most_table, _build_merge, order_by=order_by)


def update_documents(table: models.Table) -> QueryExpression:
    """Update document fields with the given values.

    Params:
    -------
    table: Table object that contains the parameters for building an update query in FQL.

    Returns:
    --------
    An FQL update query for the given collection and documents.
    """
    field_updates = {column.name: column.value for column in table.columns}
    return q.let(
        {"document_set": define_document_set(table)},
        q.do(
            q.update(
                q.select(
                    "ref",
                    q.get(q.var("document_set")),
                ),
                {"data": field_updates},
            ),
            {"data": [{"count": q.count(q.var("document_set"))}]},
        ),
    )
