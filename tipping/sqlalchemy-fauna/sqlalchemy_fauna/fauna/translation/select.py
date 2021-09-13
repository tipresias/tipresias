"""Translate a SELECT SQL query into an equivalent FQL query."""

from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import common, models, fql


def _define_single_collection_pages(sql_query: models.SQLQuery) -> QueryExpression:
    tables = sql_query.tables
    order_by = sql_query.order_by
    from_table = tables[0]

    document_set = fql.define_document_set(from_table)

    if order_by is None:
        return q.paginate(document_set, size=fql.MAX_PAGE_SIZE)

    ordered_result = q.join(
        document_set,
        q.index(
            common.index_name(
                from_table.name,
                column_name=order_by.columns[0].name,
                index_type=common.IndexType.SORT,
            )
        ),
    )
    if order_by.direction == models.OrderDirection.DESC:
        ordered_result = q.reverse(ordered_result)

    return q.map_(
        q.lambda_(["_", "ref"], q.var("ref")),
        q.paginate(ordered_result, size=fql.MAX_PAGE_SIZE),
    )


def _define_multi_collection_pages(sql_query: models.SQLQuery) -> QueryExpression:
    tables = sql_query.tables
    order_by = sql_query.order_by
    from_table = tables[0]

    if order_by is not None and order_by.columns[0].table_name != from_table.name:
        raise exceptions.NotSupportedError(
            "Fauna uses indexes for both joining and ordering of results, "
            "and we currently can only sort the principal table "
            "(i.e. the one after 'FROM') in the query. You can sort on a column "
            "from the principal table, query one table at a time, or remove "
            "the ordering constraint."
        )

    return fql.join_collections(from_table, order_by)


def _define_document_pages(sql_query: models.SQLQuery) -> QueryExpression:
    tables = sql_query.tables
    order_by = sql_query.order_by

    if order_by is not None and len(order_by.columns) > 1:
        raise exceptions.NotSupportedError(
            "Ordering by multiple columns is not yet supported."
        )

    if len(tables) > 1:
        ordered_document_set = _define_multi_collection_pages(sql_query)
    else:
        ordered_document_set = _define_single_collection_pages(sql_query)

    # Don't want to apply limit to queries with functions, because we want the calculation
    # for the entire document set, and functions only return the first row anyway
    if sql_query.limit is None or sql_query.has_functions:
        return ordered_document_set

    return q.take(sql_query.limit, ordered_document_set)


def _translate_select(
    sql_query: models.SQLQuery, document_pages: QueryExpression, distinct=False
):
    tables = sql_query.tables
    from_table = tables[0]

    get_field_value = lambda function_value, raw_value: q.if_(
        q.equals(function_value, common.NULL),
        q.if_(q.equals(raw_value, common.NULL), None, raw_value),
        q.select(["data", 0], function_value),
    )

    calculate_function_value = lambda document_set, function_name: q.if_(
        q.is_null(function_name),
        common.NULL,
        q.if_(
            q.equals(function_name, models.Function.COUNT.value),
            q.count(document_set),
            common.NULL,
        ),
    )

    # With aggregation functions, standard behaviour is to include the first value
    # if any column selections are part of the query, at least until we add support
    # for GROUP BY
    get_first_document = lambda documents: q.let(
        {"maybe_first_document": q.select(0, documents, default=common.NULL)},
        q.if_(
            q.equals(q.var("maybe_first_document"), common.NULL),
            [{}],
            [q.get(q.var("maybe_first_document"))],
        ),
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
                                from_table.name: q.merge(
                                    q.select(
                                        common.DATA, q.get(q.var("maybe_document"))
                                    ),
                                    {"ref": q.var("maybe_document")},
                                )
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
            if distinct
            else q.var("translated_documents"),
        },
        # Need to nest the results in a 'data' object if they're in the form of an array,
        # if they're paginated results, Fauna does this automatically
        q.if_(
            q.is_array(q.var("result")),
            {"data": q.var("result")},
            q.var("result"),
        ),
    )


def translate_select(sql_query: models.SQLQuery) -> QueryExpression:
    """Translate a SELECT SQL query into an equivalent FQL query.

    Params:
    -------
    sql_query: An SQLQuery instance.

    Returns:
    --------
    An FQL query expression based on the SQL query.
    """
    document_pages = _define_document_pages(sql_query)

    return _translate_select(sql_query, document_pages, distinct=sql_query.distinct)
