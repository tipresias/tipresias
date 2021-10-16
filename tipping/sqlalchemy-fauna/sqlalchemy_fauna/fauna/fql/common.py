"""Shared SQL translations and utilities for various statement types."""

import typing
import enum
import functools

from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

from sqlalchemy_fauna import exceptions, sql


NULL = "NULL"
DATA = "data"
MAX_PAGE_SIZE = 100000


class IndexType(enum.Enum):
    """Enum for the different types of Fauna indices used."""

    ALL = "all"
    REF = "ref"
    TERM = "term"
    VALUE = "value"
    SORT = "sort"


def get_foreign_key_ref(
    foreign_value: QueryExpression,
    reference_collection_name: QueryExpression,
) -> QueryExpression:
    """Get the Ref to a document associated with a foreign key value.

    Params:
    -------
    foreign_value: The value to look up, usually an ID.
    references: Field metadata dict that defines the collection (key) and field name (value)
        that the foreign key refers to.

    Returns:
    --------
    Fauna query expression that returns an array of Refs for the associated document(s).
    """
    return q.let(
        {
            "is_blank_reference": q.or_(
                q.is_null(foreign_value),
                q.equals(foreign_value, NULL),
                q.equals(reference_collection_name, NULL),
            ),
        },
        q.if_(
            q.var("is_blank_reference"),
            None,
            q.ref(q.collection(reference_collection_name), foreign_value),
        ),
    )


def index_name(
    table_name: str,
    column_name: typing.Optional[str] = None,
    index_type: IndexType = IndexType.ALL,
    foreign_key_name: typing.Optional[str] = None,
) -> str:
    """Get index name based on its configuration and internal conventions.

    Params:
    -------
    table_name: Name of the index's source collection as represented by the SQL table.
    column_name: Name of the column whose values are used to match index terms or values.
    index_type: Internal convention that determines how the index matches documents
        and what values are returned.
    """
    is_valid_column_name = (
        column_name is not None and index_type != IndexType.ALL
    ) or (column_name is None and index_type in [IndexType.ALL, IndexType.REF])
    assert is_valid_column_name

    is_valid_foreign_key_name = foreign_key_name is None or (
        foreign_key_name is not None and index_type == IndexType.REF
    )
    assert is_valid_foreign_key_name

    column_substring = "" if column_name is None else f"_by_{column_name}"
    index_type_substring = f"_{index_type.value}"
    foreign_key_substring = (
        "" if foreign_key_name is None else f"_to_{foreign_key_name}"
    )
    return table_name + column_substring + index_type_substring + foreign_key_substring


def convert_to_ref_set(
    collection_name: str, index_match: QueryExpression
) -> QueryExpression:
    """Convert value-based match set to set of refs.

    Params:
    -------
    collection_name: Name of the source collection for the index.
    index_match: Match set of the index. Index must have values attribute of the form
        [{"field": ["data", <field>]}, {"field": ["ref"}]}]
    """
    return q.join(
        index_match,
        q.lambda_(
            ["value", "ref"],
            q.match(
                q.index(index_name(collection_name, index_type=IndexType.REF)),
                q.var("ref"),
            ),
        ),
    )


def _define_match_set(query_filter: sql.Filter) -> QueryExpression:
    field_name = query_filter.column.name
    comparison_value = query_filter.value
    index_name_for_collection = functools.partial(index_name, query_filter.table_name)
    convert_to_collection_ref_set = functools.partial(
        convert_to_ref_set, query_filter.table_name
    )

    get_info_indexes_with_references = lambda collection_name, field_name: q.map_(
        q.lambda_("info_index_ref", q.get(q.var("info_index_ref"))),
        q.paginate(
            q.match(
                q.index(
                    index_name(
                        "information_schema_indexes_",
                        column_name="name_",
                        index_type=IndexType.TERM,
                    )
                ),
                index_name(
                    collection_name,
                    column_name=field_name,
                    index_type=IndexType.REF,
                ),
            ),
        ),
    )

    index_name_for_field = functools.partial(index_name_for_collection, field_name)
    equality_range = q.range(
        q.match(q.index(index_name_for_field(IndexType.VALUE))),
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
                "ref_index": q.index(index_name_for_field(IndexType.REF)),
                "term_index": q.index(index_name_for_field(IndexType.TERM)),
                "info_indexes": get_info_indexes_with_references(
                    query_filter.table_name, field_name
                ),
                "comparison_value": comparison_value,
            },
            q.if_(
                q.exists(q.var("ref_index")),
                q.match(
                    q.var("ref_index"),
                    get_foreign_key_ref(
                        q.var("comparison_value"),
                        # Assumes that there is only one reference per foreign key
                        # and that it refers to the associated collection's ID field
                        # (e.g. {'associated_table': 'id'}).
                        # This is enforced via NotSupported errors when creating collections.
                        q.select([0, DATA, "referred_table_"], q.var("info_indexes")),
                    ),
                ),
                q.if_(
                    q.exists(q.var("term_index")),
                    q.match(
                        q.var("term_index"),
                        q.var("comparison_value"),
                    ),
                    convert_to_collection_ref_set(equality_range),
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
            q.match(q.index(index_name_for_field(IndexType.VALUE))),
            [comparison_value],
            [],
        )

        if query_filter.operator == ">=":
            return convert_to_collection_ref_set(inclusive_comparison_range)

        return convert_to_collection_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    if query_filter.operator in ["<=", "<"]:
        inclusive_comparison_range = q.range(
            q.match(q.index(index_name_for_field(IndexType.VALUE))),
            [],
            [comparison_value],
        )

        if query_filter.operator == "<=":
            return convert_to_collection_ref_set(inclusive_comparison_range)

        return convert_to_collection_ref_set(
            q.difference(inclusive_comparison_range, equality_range)
        )

    raise exceptions.NotSupportedError(
        f"Unsupported operator {query_filter.operator} was received."
    )


def define_document_set(
    table: sql.Table, filter_group: typing.Optional[sql.FilterGroup]
) -> QueryExpression:
    """Build FQL match query based on filtering rules from the SQL query.

    Params:
    -------
    table: A Table object associated with a Fauna collection.

    Returns:
    --------
    FQL query expression that matches on the same conditions as the Table's filters.
    """
    filter_group_filters = [] if filter_group is None else filter_group.filters
    group_filter_names = [sql_filter.name for sql_filter in filter_group_filters]
    filters = [
        sql_filter
        for sql_filter in table.filters
        if sql_filter.name in group_filter_names
    ]

    if not any(filters):
        return q.intersection(q.match(q.index(index_name(table.name))))

    document_sets = [_define_match_set(query_filter) for query_filter in filters]
    return q.intersection(*document_sets)


def _build_intersecting_query(
    filter_group: sql.FilterGroup,
    acc_query: typing.Optional[QueryExpression],
    table: sql.Table,
    direction: str,
) -> QueryExpression:
    opposite_direction = "left" if direction == "right" else "right"
    document_set = define_document_set(table, filter_group)

    if acc_query is None:
        intersection = document_set
    else:
        intersection = q.intersection(acc_query, document_set)

    next_table = getattr(table, f"{direction}_join_table")

    if next_table is None or table.has_columns:
        return intersection

    next_join_key = getattr(table, f"{direction}_join_key")
    assert next_join_key is not None

    if next_join_key.name == "ref":
        next_foreign_key = getattr(next_table, f"{opposite_direction}_join_key")
        assert next_foreign_key is not None

        return _build_intersecting_query(
            filter_group,
            q.join(
                intersection,
                q.index(
                    index_name(
                        next_table.name,
                        column_name=next_foreign_key.name,
                        index_type=IndexType.REF,
                    )
                ),
            ),
            next_table,
            direction,
        )

    return _build_intersecting_query(
        filter_group,
        q.join(
            intersection,
            q.index(
                index_name(
                    table.name,
                    index_type=IndexType.REF,
                    foreign_key_name=next_join_key.name,
                )
            ),
        ),
        next_table,
        direction,
    )


def join_collections(sql_query: sql.SQLQuery) -> QueryExpression:
    """Join together multiple collections to return their documents in the response.

    Params:
    -------
    sql_query: SQLQuery object with information about the query params.

    Returns:
    --------
    An FQL query expression for joined and filtered documents.
    """
    tables = sql_query.tables
    order_by = sql_query.order_by
    from_table = tables[0]
    to_table = tables[-1]
    table_with_columns = next(table for table in tables if table.has_columns)

    if (
        order_by is not None
        and order_by.columns[0].table_name != table_with_columns.name
    ):
        raise exceptions.NotSupportedError(
            "Fauna uses indexes for both joining and ordering of results, "
            "and we currently can only sort the principal table "
            "(i.e. the one whose columns are being selected or modified) in the query. "
            "You can sort on a column from the principal table, query one table at a time, "
            "or remove the ordering constraint."
        )

    if not any(sql_query.filter_groups):
        raise exceptions.NotSupportedError(
            "Joining tables without cross-table filters via the WHERE clause is not supported. "
            "Selecting columns from multiple tables is not supported either, "
            "so there's no performance gain from joining tables without cross-table conditions "
            "for filtering query results."
        )

    assert from_table.left_join_table is None

    intersection_queries = []

    for filter_group in sql_query.filter_groups:
        intersection_query = q.intersection(
            *[
                _build_intersecting_query(filter_group, None, table, direction)
                for table, direction in [(from_table, "right"), (to_table, "left")]
            ]
        )

        intersection_queries.append(intersection_query)

    return q.union(*intersection_queries)


def update_documents(sql_query: sql.SQLQuery) -> QueryExpression:
    """Update document fields with the given values.

    Params:
    -------
    table: Table object that contains the parameters for building an update query in FQL.

    Returns:
    --------
    An FQL update query for the given collection and documents.
    """
    assert len(sql_query.tables) == 1
    table = sql_query.tables[0]
    assert len(sql_query.filter_groups) <= 1
    filter_group = (
        None if not any(sql_query.filter_groups) else sql_query.filter_groups[0]
    )

    field_updates = {column.name: column.value for column in table.columns}
    return q.let(
        {"document_set": define_document_set(table, filter_group)},
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
