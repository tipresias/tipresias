"""Translate a SELECT SQL query into an equivalent FQL query."""

import functools
import typing

from sqlparse import sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import common, models, fql


CalculationFunction = typing.Callable[[QueryExpression], QueryExpression]
FunctionMap = typing.Dict[str, CalculationFunction]
TableFunctionMap = typing.Dict[str, FunctionMap]


def _translate_select(sql_query: models.SQLQuery, distinct=False):
    tables = sql_query.tables
    from_table = tables[0]
    order_by = sql_query.order_by

    if order_by is not None and len(order_by.columns) > 1:
        raise exceptions.NotSupportedError(
            "Ordering by multiple columns is not yet supported."
        )

    if len(tables) > 1:
        if order_by is not None and order_by.columns[0].table_name != from_table.name:
            raise exceptions.NotSupportedError(
                "Fauna uses indexes for both joining and ordering of results, "
                "and we currently can only sort the principal table "
                "(i.e. the one after 'FROM') in the query. You can sort on a column "
                "from the principal table, query one table at a time, or remove "
                "the ordering constraint."
            )
        maybe_documents_to_select = fql.join_collections(from_table, order_by)
    else:
        document_set = fql.define_document_set(from_table)
        if order_by is None:
            maybe_documents_to_select = q.paginate(document_set, size=fql.MAX_PAGE_SIZE)
        else:
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

            maybe_documents_to_select = q.map_(
                q.lambda_(["_", "ref"], q.var("ref")),
                q.paginate(ordered_result, size=fql.MAX_PAGE_SIZE),
            )

    # Don't want to apply limit to queries with functions, because we want the calculation
    # for the entire document set, and functions only return the first row anyway
    if sql_query.limit is not None and not sql_query.has_functions:
        maybe_documents_to_select = q.take(sql_query.limit, maybe_documents_to_select)

    initial_field_alias_map: typing.Dict[str, typing.Dict[str, str]] = {}
    field_alias_map: typing.Dict[str, typing.Dict[str, str]] = functools.reduce(
        lambda alias_map, column: {
            **alias_map,
            str(column.table_name): {
                **alias_map.get(str(column.table_name), {}),
                **column.alias_map,
            },
        },
        sql_query.columns,
        initial_field_alias_map,
    )

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

    translate_fields_to_aliases = lambda collection_name, field_name: q.select(
        [collection_name, field_name],
        field_alias_map,
        default=q.var("field_name"),
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
                                        translate_fields_to_aliases(
                                            q.var("collection_name"),
                                            q.var("field_name"),
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
            "maybe_documents": maybe_documents_to_select,
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


def translate_select(sql_statement: token_groups.Statement) -> QueryExpression:
    """Translate a SELECT SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    A tuple of FQL query expression, selected column  names, and their aliases.
    """
    sql_query = models.SQLQuery.from_statement(sql_statement)

    return _translate_select(sql_query, distinct=sql_query.distinct)
