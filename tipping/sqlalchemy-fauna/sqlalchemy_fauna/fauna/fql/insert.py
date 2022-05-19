"""Translate a INSERT SQL query into an equivalent FQL query."""

import functools
import typing

from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import sql
from . import common


def translate_insert(table: sql.Table) -> typing.List[QueryExpression]:
    """Translate a INSERT SQL query into an equivalent FQL query.

    Params:
    -------
    sql_query: An SQLQuery instance.

    Returns:
    --------
    An FQL query expression.
    """
    document_to_insert = {col.name: col.value for col in table.columns}
    convert_to_collection_ref_set = functools.partial(
        common.convert_to_ref_set, "information_schema_indexes_"
    )

    # Fauna's Select doesn't play nice with null values, so we have to wrap it in an
    # if/else if the underlying value & default are null
    get_field_value = lambda document, field_name, field_info: q.let(
        {
            "referred_collection": q.select("referred_table_", field_info),
            "default_value": q.select("default_", field_info, default=common.NULL),
            "field_value": q.select(field_name, document, q.var("default_value")),
        },
        q.if_(
            q.equals(q.var("referred_collection"), common.NULL),
            q.var("field_value"),
            common.get_foreign_key_ref(
                q.var("field_value"), q.var("referred_collection")
            ),
        ),
    )

    fetch_column_info = lambda table_name: q.let(
        {
            "table_column_info": q.range(
                q.match(
                    q.index(
                        common.index_name(
                            "information_schema_columns_",
                            column_name="table_name_",
                            index_type=common.IndexType.VALUE,
                        )
                    )
                ),
                [table_name],
                [table_name],
            ),
            "table_index_info": q.range(
                q.match(
                    q.index(
                        common.index_name(
                            "information_schema_indexes_",
                            column_name="table_name_",
                            index_type=common.IndexType.VALUE,
                        )
                    )
                ),
                table_name,
                table_name,
            ),
            "reference_info": q.range(
                q.match(
                    q.index(
                        common.index_name(
                            "information_schema_indexes_",
                            column_name="referred_columns_",
                            index_type=common.IndexType.VALUE,
                        )
                    )
                ),
                ["id"],
                ["id"],
            ),
            "table_reference_info": q.intersection(
                convert_to_collection_ref_set(q.var("table_index_info")),
                convert_to_collection_ref_set(q.var("reference_info")),
            ),
            "table_references": q.to_object(
                q.select(
                    common.DATA,
                    q.map_(
                        q.lambda_(
                            "info_index_ref",
                            q.let(
                                {
                                    "index_data": q.select(
                                        common.DATA, q.get(q.var("info_index_ref"))
                                    )
                                },
                                [
                                    q.select(
                                        "constrained_columns_", q.var("index_data")
                                    ),
                                    q.select("referred_table_", q.var("index_data")),
                                ],
                            ),
                        ),
                        q.paginate(q.var("table_reference_info")),
                    ),
                )
            ),
        },
        # We filter out the ID column, because its value is automatically defined by Fauna
        q.filter_(
            q.lambda_(
                "column_info",
                q.not_(q.equals(q.select("name_", q.var("column_info")), "id")),
            ),
            q.map_(
                q.lambda_(
                    ["value", "ref"],
                    q.let(
                        {
                            "column_data": q.select(common.DATA, q.get(q.var("ref"))),
                            "column_name": q.select("name_", q.var("column_data")),
                        },
                        q.merge(
                            q.var("column_data"),
                            {
                                "referred_table_": q.select(
                                    q.var("column_name"),
                                    q.var("table_references"),
                                    default=common.NULL,
                                )
                            },
                        ),
                    ),
                ),
                q.paginate(q.var("table_column_info")),
            ),
        ),
    )

    build_document = lambda column_info: q.let(
        {
            "document": document_to_insert,
            "field_items": q.map_(
                q.lambda_(
                    "field_info",
                    q.let(
                        {"field_name": q.select("name_", q.var("field_info"))},
                        [
                            q.var("field_name"),
                            get_field_value(
                                q.var("document"),
                                q.var("field_name"),
                                q.var("field_info"),
                            ),
                        ],
                    ),
                ),
                column_info,
            ),
        },
        q.to_object(q.select(common.DATA, q.var("field_items"))),
    )

    flatten_response_fields = lambda response: q.to_object(
        q.union(
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
                q.to_array(response),
            )
        )
    )

    # We map over field_metadata, with the ref ID inserted first, to build the document object
    # in order to maintain the order of fields as queried. Otherwise, SQLAlchemy
    # gets confused and assigns values to the incorrect keys.
    get_collection_field_names = lambda column_info: q.union(
        ["ref"],
        q.select(
            common.DATA,
            q.filter_(
                q.lambda_(
                    "column_name",
                    q.not_(q.equals(q.var("column_name"), "id")),
                ),
                q.map_(
                    q.lambda_(
                        "column_doc",
                        q.select("name_", q.var("column_doc")),
                    ),
                    column_info,
                ),
            ),
        ),
    )
    # We convert 'ref' back into 'id' in the response, because that's the primary key
    # that SQLAlchemy expects.
    get_response_field_name = lambda field_name: q.if_(
        q.equals(field_name, "ref"),
        "id",
        field_name,
    )
    get_response_field_value = lambda document, field_name: q.select(
        field_name, document, default=common.NULL
    )
    build_document_response = lambda document, column_info: q.to_object(
        q.map_(
            q.lambda_(
                "field_name",
                [
                    get_response_field_name(q.var("field_name")),
                    get_response_field_value(document, q.var("field_name")),
                ],
            ),
            get_collection_field_names(column_info),
        )
    )

    return q.let(
        {
            "column_info": fetch_column_info(table.name),
            "created_doc": q.create(
                q.collection(table.name),
                {"data": build_document(q.var("column_info"))},
            ),
            "flattened_doc": flatten_response_fields(q.var("created_doc")),
        },
        {
            "data": [
                build_document_response(q.var("flattened_doc"), q.var("column_info"))
            ],
        },
    )
