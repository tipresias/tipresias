"""Translate a SELECT SQL query into an equivalent FQL query."""

import typing
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions, sql
from . import common


def _sort_document_set(
    document_set: QueryExpression, order_by: typing.Optional[sql.OrderBy]
):
    if order_by is None:
        return q.paginate(document_set, size=common.MAX_PAGE_SIZE)

    if len(order_by.columns) > 1:
        raise exceptions.NotSupportedError(
            "Ordering by multiple columns is not yet supported."
        )

    ordered_column = order_by.columns[0]
    assert ordered_column.table_name is not None

    ordered_document_set = q.join(
        document_set,
        q.index(
            common.index_name(
                ordered_column.table_name,
                column_name=ordered_column.name,
                index_type=common.IndexType.SORT,
            )
        ),
    )
    if order_by.direction == sql.OrderDirection.DESC:
        ordered_document_set = q.reverse(ordered_document_set)

    return q.map_(
        q.lambda_(["_", "ref"], q.var("ref")),
        q.paginate(ordered_document_set, size=common.MAX_PAGE_SIZE),
    )


def _define_document_pages(sql_query: sql.SQLQuery) -> QueryExpression:
    tables = sql_query.tables
    order_by = sql_query.order_by

    if len(tables) > 1:
        document_set = common.join_collections(sql_query)
    else:
        document_set = common.build_document_set(sql_query.filter_group, tables[0])

    ordered_document_set = _sort_document_set(document_set, order_by)
    # Don't want to apply limit to queries with functions, because we want the calculation
    # for the entire document set, and functions only return the first row anyway
    if sql_query.limit is None or sql_query.has_functions:
        return ordered_document_set

    return q.take(sql_query.limit, ordered_document_set)


def translate_select(sql_query: sql.SQLQuery) -> QueryExpression:
    """Translate a SELECT SQL query into an equivalent FQL query.

    Params:
    -------
    sql_query: An SQLQuery instance.

    Returns:
    --------
    An FQL query expression based on the SQL query.
    """
    document_pages = _define_document_pages(sql_query)
    selected_table = next(table for table in sql_query.tables if table.has_columns)

    get_field_value = lambda function_value, raw_value: q.if_(
        q.equals(function_value, common.NULL),
        q.if_(q.equals(raw_value, common.NULL), None, raw_value),
        q.select([common.DATA, 0], function_value),
    )

    calculate_function_value = lambda document_set, function_name: q.if_(
        q.is_null(function_name),
        common.NULL,
        q.if_(
            q.equals(function_name, sql.Function.COUNT.value),
            q.count(document_set),
            common.NULL,
        ),
    )

    # With aggregation functions, standard behaviour is to include the first value
    # if any column selections are part of the query, at least until we add support
    # for GROUP BY
    get_first_document = lambda documents: q.if_(
        q.is_empty(documents), [{}], q.take(1, documents)
    )

    translate_document_fields = lambda maybe_documents: q.let(
        {
            # We map over selected_fields to build document object
            # to maintain the order of fields as queried. Otherwise,
            # SQLAlchemy gets confused and assigns values to the incorrect keys.
            "selected_column_info": [
                [col.table_name, col.name, col.function_name]
                for col in sql_query.columns
            ],
            "has_functions": any(col.function_name for col in sql_query.columns),
            "maybe_document_set": q.if_(
                q.var("has_functions"),
                get_first_document(maybe_documents),
                maybe_documents,
            ),
            "field_alias_map": sql_query.alias_map,
        },
        q.map_(
            q.lambda_(
                "maybe_document",
                q.let(
                    {
                        "document": q.if_(
                            q.is_ref(q.var("maybe_document")),
                            {
                                # We use the selected table name here instead of deriving
                                # the collection name from the document ref in order to
                                # save a 'get' call from inside of a map, which could get
                                # expensive.
                                selected_table.name: q.merge(
                                    q.select(
                                        common.DATA,
                                        q.get(q.var("maybe_document")),
                                    ),
                                    {"ref": q.var("maybe_document")},
                                ),
                            },
                            q.var("maybe_document"),
                        ),
                    },
                    q.to_object(
                        q.map_(
                            q.lambda_(
                                ["collection_name", "field_name", "function_name"],
                                q.let(
                                    {
                                        "function_value": calculate_function_value(
                                            maybe_documents, q.var("function_name")
                                        ),
                                        "raw_value": q.select(
                                            [
                                                q.var("collection_name"),
                                                q.var("field_name"),
                                            ],
                                            q.var("document"),
                                            default=common.NULL,
                                        ),
                                    },
                                    [
                                        q.select(
                                            [
                                                q.var("collection_name"),
                                                q.var("field_name"),
                                            ],
                                            q.var("field_alias_map"),
                                        ),
                                        get_field_value(
                                            q.var("function_value"), q.var("raw_value")
                                        ),
                                    ],
                                ),
                            ),
                            q.var("selected_column_info"),
                        )
                    ),
                ),
            ),
            q.var("maybe_document_set"),
        ),
    )

    return q.let(
        {
            "maybe_documents": document_pages,
            "translated_documents": translate_document_fields(q.var("maybe_documents")),
            "result": q.distinct(q.var("translated_documents"))
            if sql_query.distinct
            else q.var("translated_documents"),
        },
        # Paginated sets hold an array of results in a 'data' field, so we try to flatten it
        # in case we're dealing with pages instead of an array of results which doesn't
        # have such nesting
        {common.DATA: q.select(common.DATA, q.var("result"), q.var("result"))},
    )
