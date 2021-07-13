"""Translate a SELECT SQL query into an equivalent FQL query."""

import typing
from functools import reduce, partial

from sqlparse import tokens as token_types, sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from . import common
from .models import Column, Table


CalculationFunction = typing.Callable[[QueryExpression], QueryExpression]
FunctionMap = typing.Dict[str, CalculationFunction]
TableFunctionMap = typing.Dict[str, FunctionMap]

MAX_PAGE_SIZE = 100000


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
            "AVG and SUM functions are not yet supported."
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
    documents_to_select: QueryExpression,
    field_alias_map: common.FieldAliasMap,
    field_functions: FunctionMap,
):
    document_items = q.to_array(q.get(q.var("document")))
    flattened_items = q.union(
        q.map_(
            q.lambda_(
                ["key", "value"],
                q.if_(
                    q.equals(q.var("key"), common.DATA),
                    q.to_array(q.var("value")),
                    # We put single key/value pairs in nested arrays to match
                    # the structure of the nested 'data' key/values
                    [[q.var("key"), q.var("value")]],
                ),
            ),
            document_items,
        )
    )

    selected_fields = list(field_alias_map.keys())
    field_alias = q.select(
        q.var("field"),
        field_alias_map,
        default=q.var("field"),
    )

    field_function = q.select(q.var("field"), field_functions, default=common.NULL)
    basic_field = q.select(q.var("field"), q.to_object(flattened_items))
    field_value = q.if_(
        q.equals(field_function, common.NULL), basic_field, field_function
    )
    translate_to_alias = q.lambda_("field", [field_alias, field_value])
    # We map over selected_fields to build document object to maintain the order
    # of fields as queried. Otherwise, SQLAlchemy gets confused and assigns values
    # to the incorrect keys.
    aliased_document = q.to_object(q.map_(translate_to_alias, selected_fields))

    paginated_documents = q.paginate(q.var("documents"), size=MAX_PAGE_SIZE)
    # With aggregation functions, standard behaviour is to include the first value
    # if any column selections are part of the query, at least until we add support
    # for GROUP BY
    first_document = q.select(0, paginated_documents, default={})
    query_response = q.let(
        {"documents": documents_to_select},
        q.map_(
            q.lambda_("document", aliased_document),
            [first_document],
        ),
    )

    return q.let(
        {"response": query_response},
        {common.DATA: q.var("response")},
    )


def _translate_select_without_functions(
    documents_to_select: QueryExpression,
    field_alias_map: common.FieldAliasMap,
    distinct=False,
):
    flatten = lambda items: q.union(
        q.map_(
            q.lambda_(
                ["key", "value"],
                q.if_(
                    q.equals(q.var("key"), common.DATA),
                    q.to_array(q.var("value")),
                    # We put single key/value pairs in nested arrays to match
                    # the structure of the nested 'data' key/values
                    [[q.var("key"), q.var("value")]],
                ),
            ),
            items,
        )
    )

    translate_fields_to_aliases = lambda document_fields: q.lambda_(
        "field",
        q.let(
            {
                "field_name": q.select(
                    q.var("field"), field_alias_map, default=q.var("field")
                ),
                "field_value": q.select(
                    q.var("field"), document_fields, default=common.NULL
                ),
            },
            [
                q.var("field_name"),
                q.if_(
                    q.equals(q.var("field_value"), common.NULL),
                    None,
                    q.var("field_value"),
                ),
            ],
        ),
    )

    # We map over selected_fields to build document object to maintain the order
    # of fields as queried. Otherwise, SQLAlchemy gets confused and assigns values
    # to the incorrect keys.
    selected_fields = list(field_alias_map.keys())
    select_document_fields = q.lambda_(
        "document",
        q.to_object(
            q.map_(
                translate_fields_to_aliases(
                    q.to_object(flatten(q.to_array(q.get(q.var("document")))))
                ),
                selected_fields,
            )
        ),
    )
    translate_documents = lambda documents: q.map_(
        select_document_fields,
        q.paginate(documents, size=MAX_PAGE_SIZE),
    )

    return q.let(
        {"documents": documents_to_select},
        q.distinct(translate_documents(q.var("documents")))
        if distinct
        else translate_documents(q.var("documents")),
    )


def _translate_select_from_table(
    statement: token_groups.Statement, table: Table
) -> QueryExpression:
    _, wildcard = statement.token_next_by(t=(token_types.Wildcard))

    if wildcard is not None:
        raise exceptions.NotSupportedError("Wildcards ('*') are not yet supported")

    _, distinct = statement.token_next_by(m=(token_types.Keyword, "DISTINCT"))

    idx, identifiers = statement.token_next_by(
        i=(token_groups.Identifier, token_groups.IdentifierList, token_groups.Function)
    )

    for column in Column.from_identifier_group(identifiers):
        table.add_column(column)

    _, where_group = statement.token_next_by(i=token_groups.Where, idx=idx)
    documents_to_select = common.parse_where(where_group, table)

    table_functions = _parse_functions(q.var("documents"), identifiers, table.name)
    field_functions = table_functions[table.name]

    return (
        _translate_select_with_functions(
            documents_to_select, table.column_alias_map, field_functions
        )
        if len(field_functions)
        else _translate_select_without_functions(
            documents_to_select, table.column_alias_map, distinct=distinct
        )
    )


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
        q.paginate(q.indexes(), size=MAX_PAGE_SIZE),
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
        q.paginate(q.collections(), size=MAX_PAGE_SIZE),
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

    if table_identifier is None:
        raise exceptions.NotSupportedError(
            "Only one table per query is currently supported"
        )

    table = Table(table_identifier)

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

    return [_translate_select_from_table(statement, table)]
