"""Translate a SELECT SQL query into an equivalent FQL query."""

import functools
import typing
from functools import reduce, partial

from sqlparse import tokens as token_types, sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import common, models, fql


CalculationFunction = typing.Callable[[QueryExpression], QueryExpression]
FunctionMap = typing.Dict[str, CalculationFunction]
TableFunctionMap = typing.Dict[str, FunctionMap]


def _parse_function(
    collection: QueryExpression,
    function_map: typing.Dict[str, typing.Any],
    identifier: token_groups.Identifier,
) -> TableFunctionMap:
    if not isinstance(identifier, token_groups.Identifier):
        return function_map

    _, function_token = identifier.token_next_by(i=token_groups.Function)

    if function_token is None:
        return function_map

    function_name = function_token.value
    _, function_id = function_token.token_next_by(i=token_groups.Identifier)
    _, function_type = function_id.token_next_by(t=token_types.Name)
    _, parenthesis = function_token.token_next_by(i=token_groups.Parenthesis)
    _, table_column_identifier = parenthesis.token_next_by(i=token_groups.Identifier)
    _, table_column_separator = table_column_identifier.token_next_by(
        m=(token_types.Punctuation, ".")
    )

    if table_column_separator is None:
        table_name = None
    else:
        _, table = table_column_identifier.token_next_by(t=token_types.Name)
        table_name = table.value

    if function_type.value.lower() == "count":
        calculation = q.count(collection)
    else:
        raise exceptions.NotSupportedError(
            "MIN, MAX, AVG, and SUM functions are not yet supported."
        )

    if table_name is None:
        assert len(function_map.keys()) == 1
        return {
            key: {**value, function_name: calculation}
            for key, value in function_map.items()
        }

    return {
        **function_map,
        table_name: {**function_map.get(table_name, {}), function_name: calculation},
    }


def _parse_functions(
    collection: QueryExpression,
    identifiers: typing.Union[
        token_groups.Identifier, token_groups.IdentifierList, token_groups.Function
    ],
    table_name: str,
) -> TableFunctionMap:
    parse_function = partial(_parse_function, collection)

    if isinstance(identifiers, token_groups.Function):
        return parse_function({table_name: {}}, token_groups.Identifier([identifiers]))

    if isinstance(identifiers, token_groups.Identifier):
        return parse_function({table_name: {}}, identifiers)

    return reduce(parse_function, identifiers, {table_name: {}})


def _translate_select_with_functions(
    table: models.Table,
    field_functions: FunctionMap,
):
    documents_to_select = fql.define_document_set(table)
    field_alias_map = table.column_alias_map
    selected_fields = list(field_alias_map.keys())

    apply_alias = lambda field_name: q.select(
        field_name, field_alias_map, default=field_name
    )

    extract_basic_field_value = lambda document, field_name: q.let(
        {"value": q.select(field_name, document, common.NULL)},
        q.if_(q.equals(q.var("value"), common.NULL), None, q.var("value")),
    )
    extract_document_value = lambda document, field_name: q.select(
        field_name,
        field_functions,
        default=extract_basic_field_value(document, field_name),
    )
    translate_to_alias = lambda document, field_name: [
        apply_alias(field_name),
        extract_document_value(document, field_name),
    ]

    flatten_document_fields = lambda document: q.let(
        {
            "field_items": q.map_(
                q.lambda_(
                    ["field_name", "field_value"],
                    q.if_(
                        q.equals(q.var("field_name"), common.DATA),
                        q.to_array(q.var("field_value")),
                        # We put single key/value pairs in nested arrays to match
                        # the structure of the nested 'data' key/values
                        [[q.var("field_name"), q.var("field_value")]],
                    ),
                ),
                q.to_array(document),
            ),
            "flattened_items": q.if_(
                q.is_empty(q.var("field_items")),
                q.var("field_items"),
                q.union(q.var("field_items")),
            ),
        },
        q.to_object(q.var("flattened_items")),
    )
    # We map over selected_fields to build document object to maintain the order
    # of fields as queried. Otherwise, SQLAlchemy gets confused and assigns values
    # to the incorrect keys.
    apply_field_aliases = lambda document: q.to_object(
        q.map_(
            q.lambda_(
                "field_name",
                translate_to_alias(document, q.var("field_name")),
            ),
            selected_fields,
        )
    )

    # With aggregation functions, standard behaviour is to include the first value
    # if any column selections are part of the query, at least until we add support
    # for GROUP BY
    get_first_document = lambda documents: q.let(
        {
            "first_document": q.select(
                0, q.paginate(documents, size=fql.MAX_PAGE_SIZE), default=common.NULL
            )
        },
        q.if_(
            q.equals(q.var("first_document"), common.NULL),
            {},
            q.get(q.var("first_document")),
        ),
    )

    return q.let(
        {
            "documents": documents_to_select,
            "response": apply_field_aliases(
                flatten_document_fields(get_first_document((q.var("documents"))))
            ),
        },
        {common.DATA: [q.var("response")]},
    )


def _translate_select_without_functions(sql_query: models.SQLQuery, distinct=False):
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

    if sql_query.limit is not None:
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

    translate_fields_to_aliases = lambda document: q.lambda_(
        ["collection_name", "field_name"],
        q.let(
            {
                "alias_name": q.select(
                    [q.var("collection_name"), q.var("field_name")],
                    field_alias_map,
                    default=q.var("field_name"),
                ),
                "field_value": q.select(
                    [q.var("collection_name"), q.var("field_name")],
                    document,
                    default=common.NULL,
                ),
            },
            [
                q.var("alias_name"),
                q.if_(
                    q.equals(q.var("field_value"), common.NULL),
                    None,
                    q.var("field_value"),
                ),
            ],
        ),
    )

    translate_document_fields = q.lambda_(
        "maybe_document",
        q.let(
            {
                "document": q.if_(
                    q.is_ref(q.var("maybe_document")),
                    {
                        from_table.name: q.merge(
                            q.select(common.DATA, q.get(q.var("maybe_document"))),
                            {"ref": q.var("maybe_document")},
                        )
                    },
                    q.var("maybe_document"),
                ),
            },
            q.to_object(
                q.map_(
                    translate_fields_to_aliases(q.var("document")),
                    # We map over selected_fields to build document object to maintain the order
                    # of fields as queried. Otherwise, SQLAlchemy gets confused and assigns values
                    # to the incorrect keys.
                    [[col.table_name, col.name] for col in sql_query.columns],
                )
            ),
        ),
    )
    translate_documents = lambda maybe_documents: q.map_(
        translate_document_fields, maybe_documents
    )

    return q.let(
        {
            "maybe_documents": maybe_documents_to_select,
            "translated_documents": translate_documents(q.var("maybe_documents")),
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


def _translate_select_from_table(
    statement: token_groups.Statement, sql_query: models.SQLQuery
) -> QueryExpression:
    _, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList, token_groups.Function)
    )
    tables = sql_query.tables

    for table in tables:
        table_functions = _parse_functions(q.var("documents"), identifiers, table.name)
        field_functions = table_functions[table.name]

        if any(field_functions):
            if len(tables) > 1:
                raise exceptions.NotSupportedError(
                    "SQL functions across multiple tables are not yet supported."
                )

            return _translate_select_with_functions(table, field_functions)

    return _translate_select_without_functions(sql_query, distinct=sql_query.distinct)


def _translate_select_from_info_schema_constraints(
    statement: token_groups.Statement,
) -> QueryExpression:
    # We don't use the standard logic for parsing this WHERE clause,
    # because sqlparse treats WHERE clauses in INFORMATION_SCHEMA queries
    # differently, returning flat tokens in the WHERE group
    # instead of nested token groups.
    _, where_group = statement.token_next_by(i=token_groups.Where)

    if where_group is None:
        raise exceptions.NotSupportedError(
            "A 'WHERE TABLE_NAME = <table_name>' clause is required when querying "
            "'INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE'"
        )

    idx, condition_column = where_group.token_next_by(
        m=(token_types.Keyword, "TABLE_NAME")
    )

    if condition_column is None:
        raise exceptions.NotSupportedError(
            "Only TABLE_NAME condition is supported for "
            "SELECT FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE"
        )

    idx, condition = where_group.token_next_by(m=(token_types.Comparison, "="), idx=idx)

    if condition is None:
        raise exceptions.NotSupportedError(
            "Only column-value-based conditions (e.g. WHERE <column> = <value>) "
            "are currently supported."
        )

    _, condition_check = where_group.token_next(idx, skip_ws=True)
    condition_value = common.extract_value(condition_check)

    is_based_on_collection = q.lambda_(
        "index",
        q.equals(
            q.select(["source", "id"], q.get(q.var("index"))),
            condition_value,
        ),
    )
    indexes_based_on_collection = q.filter_(
        is_based_on_collection,
        q.paginate(q.indexes(), size=fql.MAX_PAGE_SIZE),
    )

    collection_fields = q.select(
        [common.DATA, "metadata", "fields"],
        q.get(q.collection(condition_value)),
    )
    collection_field_names = q.map_(
        q.lambda_(
            ["field_name", "field_metadata"],
            q.if_(q.equals(q.var("field_name"), "ref"), "id", q.var("field_name")),
        ),
        q.to_array(collection_fields),
    )

    index = q.get(q.var("index"))
    # We select the last one, because the first field listed is 'data'
    last_field_name = q.select(q.subtract(q.count(q.var("field")), 1), q.var("field"))
    term_field = (
        q.let(
            {"field": q.select("field", q.var("term"))},
            q.if_(q.equals("ref", last_field_name), "id", last_field_name),
        ),
    )
    index_term_fields = q.union(
        q.map_(
            q.lambda_("term", term_field),
            q.select("terms", index),
        )
    )
    column_names = q.if_(
        q.contains_field("terms", index),
        index_term_fields,
        collection_field_names,
    )
    index_response = {
        "name": q.select("name", index),
        "column_names": q.concat(column_names, separator=","),
        # Fauna doesn't seem to return a 'unique' field with index queries,
        # and we don't really need it, so leaving it blank for now.
        "unique": False,
    }

    return q.map_(
        q.lambda_("index", index_response),
        indexes_based_on_collection,
    )


def _translate_select_from_info_schema_columns(
    statement: token_groups.Statement,
) -> QueryExpression:
    # We don't use the standard logic for parsing this WHERE clause,
    # because sqlparse treats WHERE clauses in INFORMATION_SCHEMA queries
    # differently, returning flat tokens in the WHERE group
    # instead of nested token groups.
    _, where_group = statement.token_next_by(i=token_groups.Where)

    if where_group is None:
        raise exceptions.NotSupportedError(
            "A 'WHERE TABLE_NAME = <table_name>' clause is required when querying "
            "'INFORMATION_SCHEMA.COLUMNS'"
        )

    idx, condition_column = where_group.token_next_by(
        m=(token_types.Keyword, "TABLE_NAME")
    )

    if condition_column is None:
        raise exceptions.NotSupportedError(
            "Only TABLE_NAME condition is supported for SELECT COLUMN_NAME"
        )

    idx, condition = where_group.token_next_by(m=(token_types.Comparison, "="), idx=idx)

    if condition is None:
        raise exceptions.NotSupportedError(
            "Only column-value-based conditions (e.g. WHERE <column> = <value>) "
            "are currently supported."
        )

    _, condition_check = where_group.token_next(idx, skip_ws=True)
    condition_value = common.extract_value(condition_check)

    collection = q.collection(condition_value)
    field_metadata = q.select(
        [common.DATA, "metadata", "fields"],
        q.get(collection),
    )
    # Selecting column info from INFORMATION_SCHEMA returns foreign keys
    # as regular columns, so we don't need the extra table-reference info
    metadata_without_references = q.filter_(
        q.lambda_(
            ["metadata_type", "metadata"],
            q.not_(q.equals(q.var("metadata_type"), "references")),
        ),
        q.to_array(q.var("field_data")),
    )
    flattened_metadata = q.union(
        [["name", q.var("field_name")]], metadata_without_references
    )
    metadata_response = q.map_(
        q.lambda_(
            ["field_name", "field_data"],
            q.to_object(flattened_metadata),
        ),
        q.to_array(field_metadata),
    )
    id_column = {
        "name": "id",
        "unique": True,
        "not_null": True,
        "type": "String",
    }

    return q.let(
        {
            "response": {
                common.DATA: q.union(
                    [id_column],
                    metadata_response,
                )
            }
        },
        q.var("response"),
    )


def _translate_select_from_info_schema_tables() -> QueryExpression:
    collection = q.get(q.var("collection"))
    select_ref = q.filter_(
        q.lambda_(["key", "_"], q.equals(q.var("key"), "ref")),
        q.to_array(collection),
    )
    table_items = q.map_(
        q.lambda_(
            ["_", "value"],
            ["id", q.var("value")],
        ),
        select_ref,
    )
    get_collection_ref = q.lambda_("collection", q.to_object(table_items))

    return q.map_(
        get_collection_ref,
        q.paginate(q.collections(), size=fql.MAX_PAGE_SIZE),
    )


def translate_select(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate a SELECT SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    A tuple of FQL query expression, selected column  names, and their aliases.
    """
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
    _, table_identifier = statement.token_next_by(i=(token_groups.Identifier), idx=idx)

    # If we can't find a single table identifier, it means that multiple tables
    # are referenced in the FROM clause, which isn't supported.
    if table_identifier is None:
        raise exceptions.NotSupportedError(
            "Only one table per query is currently supported"
        )

    table = models.Table.from_identifier(table_identifier)

    # TODO: As I've looked into INFORMATION_SCHEMA queries more, I realise
    # that these aren't returning valid responses for the given SQL queries,
    # but just the data that SQLAlchemy needs for some of the Dialect methods.
    # It's okay for now, but should probably fix these query responses eventually
    # and put the SQLAlchemy-specific logic/transformation in FaunaDialect
    if table.name == "INFORMATION_SCHEMA.TABLES":
        return [_translate_select_from_info_schema_tables()]

    if table.name == "INFORMATION_SCHEMA.COLUMNS":
        return [_translate_select_from_info_schema_columns(statement)]

    if table.name == "INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE":
        return [_translate_select_from_info_schema_constraints(statement)]

    # TODO: We have duplicate logic defining tables, because INFORMATION_SCHEMA queries
    # are a special case that are going to require a rewrite eventually, so easier
    # to ignore them for now in order to progress with this refactor.
    sql_query = models.SQLQuery.from_statement(statement)
    return [_translate_select_from_table(statement, sql_query)]
