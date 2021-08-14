"""Translate a CREATE SQL query into an equivalent FQL query."""

import typing
from datetime import datetime
from functools import partial, reduce
from copy import deepcopy

from sqlparse import tokens as token_types
from sqlparse import sql as token_groups
from faunadb import query as q
from faunadb.objects import _Expr as QueryExpression
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions
from . import common


FieldMetadata = TypedDict(
    "FieldMetadata",
    {
        "unique": bool,
        "not_null": bool,
        "default": typing.Union[str, int, float, bool, datetime, None],
        "type": str,
        "references": typing.Dict[str, str],
    },
)
FieldsMetadata = typing.Dict[str, FieldMetadata]
CollectionMetadata = TypedDict("CollectionMetadata", {"fields": FieldsMetadata})


EMPTY_DICT: typing.Dict[str, typing.Any] = {}
DEFAULT_FIELD_METADATA: FieldMetadata = {
    "unique": False,
    "not_null": False,
    "default": None,
    "type": "",
    "references": EMPTY_DICT,
}

DATA_TYPE_MAP = {
    "CHAR": "String",
    "VARCHAR": "String",
    "BINARY": "String",
    "VARBINARY": "String",
    "TINYBLOB": "String",
    "TINYTEXT": "String",
    "TEXT": "String",
    "BLOB": "String",
    "MEDIUMTEXT": "String",
    "MEDIUMBLOB": "String",
    "LONGTEXT": "String",
    "LONGBLOB": "String",
    "ENUM": "String",
    "SET": "String",
    "BIT": "Integer",
    "TINYINT": "Integer",
    "SMALLINT": "Integer",
    "MEDIUMINT": "Integer",
    "INT": "Integer",
    "INTEGER": "Integer",
    "BIGINT": "Integer",
    "FLOAT": "Float",
    "DOUBLE": "Float",
    "DOUBLE PRECISION": "Float",
    "DECIMAL": "Float",
    "DEC": "Float",
    "BOOL": "Boolean",
    "BOOLEAN": "Boolean",
    "YEAR": "Integer",
    "DATE": "Date",
    "DATETIME": "TimeStamp",
    "TIMESTAMP": "TimeStamp",
    # Fauna has no concept of time independent of the date
    "TIME": "String",
}


def _contains_column_name(
    token_group: typing.Union[
        token_groups.TokenList,
        token_groups.IdentifierList,
        token_groups.Identifier,
        token_groups.Parenthesis,
    ],
    idx: int,
) -> bool:
    return token_group.token_next_by(t=token_types.Name, idx=idx) != (None, None)


def _define_primary_key(
    metadata: FieldsMetadata,
    column_definition_group: token_groups.TokenList,
) -> typing.Optional[FieldsMetadata]:
    idx, constraint_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "CONSTRAINT")
    )

    idx, primary_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "PRIMARY"), idx=(idx or -1)
    )

    if constraint_keyword is not None and primary_keyword is None:
        raise exceptions.NotSupportedError(
            "When a column definition clause begins with CONSTRAINT, "
            "only a PRIMARY KEY constraint is supported"
        )

    if primary_keyword is None:
        return None

    # If the keyword isn't followed by column name(s), then it's part of
    # a regular column definition and should be handled by _define_column
    if not _contains_column_name(column_definition_group, idx):
        return None

    new_metadata: FieldsMetadata = deepcopy(metadata)

    while True:
        idx, primary_key_column = column_definition_group.token_next_by(
            t=token_types.Name, idx=idx
        )

        # 'id' is defined and managed by Fauna, so we ignore any attempts
        # to manage it from SQLAlchemy
        if primary_key_column is None or primary_key_column.value == "id":
            break

        primary_key_column_name = primary_key_column.value

        new_metadata[primary_key_column_name] = {
            **DEFAULT_FIELD_METADATA,  # type: ignore
            **new_metadata.get(primary_key_column_name, {}),  # type: ignore
            "unique": True,
            "not_null": True,
        }

    return new_metadata


def _define_unique_constraint(
    metadata: FieldsMetadata,
    column_definition_group: token_groups.TokenList,
) -> typing.Optional[FieldsMetadata]:
    idx, unique_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "UNIQUE")
    )

    if unique_keyword is None:
        return None

    # If the keyword isn't followed by column name(s), then it's part of
    # a regular column definition and should be handled by _define_column
    if not _contains_column_name(column_definition_group, idx):
        return None

    new_metadata = deepcopy(metadata)

    while True:
        idx, unique_key_column = column_definition_group.token_next_by(
            t=token_types.Name, idx=idx
        )

        # 'id' is defined and managed by Fauna, so we ignore any attempts
        # to manage it from SQLAlchemy
        if unique_key_column is None or unique_key_column.value == "id":
            break

        unique_key_column_name = unique_key_column.value

        new_metadata[unique_key_column_name] = {
            **DEFAULT_FIELD_METADATA,  # type: ignore
            **new_metadata.get(unique_key_column_name, {}),  # type: ignore
            "unique": True,
        }

    return new_metadata


def _define_foreign_key_constraint(
    metadata: FieldsMetadata, column_definition_group: token_groups.TokenList
) -> typing.Optional[FieldsMetadata]:
    idx, foreign_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "FOREIGN")
    )
    if foreign_keyword is None:
        return None

    idx, _ = column_definition_group.token_next_by(m=(token_types.Name, "KEY"), idx=idx)
    idx, foreign_key_column = column_definition_group.token_next_by(
        t=token_types.Name, idx=idx
    )
    column_name = foreign_key_column.value

    idx, _ = column_definition_group.token_next_by(
        m=(token_types.Keyword, "REFERENCES"), idx=idx
    )
    idx, reference_table = column_definition_group.token_next_by(
        t=token_types.Name, idx=idx
    )
    reference_table_name = reference_table.value
    idx, reference_column = column_definition_group.token_next_by(
        t=token_types.Name, idx=idx
    )
    reference_column_name = reference_column.value

    if any(metadata.get(column_name, EMPTY_DICT).get("references", EMPTY_DICT)):
        raise exceptions.NotSupportedError(
            "Foreign keys with multiple references are not currently supported."
        )

    if reference_column_name != "id":
        raise exceptions.NotSupportedError(
            "Foreign keys referring to fields other than ID are not currently supported."
        )

    return {
        **metadata,
        column_name: {
            **DEFAULT_FIELD_METADATA,  # type: ignore
            **metadata.get(column_name, EMPTY_DICT),
            "references": {reference_table_name: reference_column_name},
        },
    }


def _define_column(
    metadata: FieldsMetadata,
    column_definition_group: token_groups.TokenList,
) -> FieldsMetadata:
    idx, column = column_definition_group.token_next_by(t=token_types.Name)
    column_name = column.value

    # "id" is auto-generated by Fauna, so we ignore it in SQL column definitions
    if column_name == "id":
        return metadata

    idx, data_type = column_definition_group.token_next_by(t=token_types.Name, idx=idx)
    _, not_null_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "NOT NULL")
    )
    _, unique_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "UNIQUE")
    )
    _, primary_key_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "PRIMARY KEY")
    )
    _, default_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "DEFAULT")
    )
    _, check_keyword = column_definition_group.token_next_by(
        m=(token_types.Keyword, "CHECK")
    )

    if check_keyword is not None:
        raise exceptions.NotSupportedError("CHECK keyword is not supported.")

    column_metadata: typing.Union[FieldMetadata, typing.Dict[str, str]] = metadata.get(
        column_name, {}
    )
    is_primary_key = primary_key_keyword is not None
    is_not_null = (
        not_null_keyword is not None
        or is_primary_key
        or column_metadata.get("not_null")
        or False
    )
    is_unique = (
        unique_keyword is not None
        or is_primary_key
        or column_metadata.get("unique")
        or False
    )
    default_value = (
        default_keyword
        if default_keyword is None
        else common.extract_value(default_keyword.value)
    )

    return {
        **metadata,
        column_name: {
            **DEFAULT_FIELD_METADATA,  # type: ignore
            **metadata.get(column_name, EMPTY_DICT),  # type: ignore
            "unique": is_unique,
            "not_null": is_not_null,
            "default": default_value,
            "type": DATA_TYPE_MAP[data_type.value],
        },
    }


def _build_fields_metadata(
    metadata: FieldsMetadata,
    column_definition_group: token_groups.TokenList,
) -> FieldsMetadata:
    return (
        _define_primary_key(metadata, column_definition_group)
        or _define_foreign_key_constraint(metadata, column_definition_group)
        or _define_unique_constraint(metadata, column_definition_group)
        or _define_column(metadata, column_definition_group)
    )


def _split_column_identifiers_by_comma(
    column_identifiers: token_groups.IdentifierList,
) -> typing.List[token_groups.TokenList]:
    column_tokens = list(column_identifiers.flatten())
    column_token_list = token_groups.TokenList(column_tokens)
    comma_idxs: typing.List[typing.Optional[int]] = [None]
    comma_idx = -1

    while True:
        if comma_idx is None:
            break

        comma_idx, _ = column_token_list.token_next_by(
            m=(token_types.Punctuation, ","), idx=comma_idx
        )

        comma_idxs.append(comma_idx)

    column_group_ranges = [
        (comma_idxs[comma_idx], comma_idxs[comma_idx + 1])
        for comma_idx in range(0, len(comma_idxs) - 1)
    ]

    return [
        token_groups.TokenList(
            column_tokens[(start if start is None else start + 1) : stop]
        )
        for start, stop in column_group_ranges
    ]


def _extract_column_definitions(
    column_identifiers: token_groups.IdentifierList,
) -> FieldsMetadata:
    # sqlparse doesn't group column info correctly within the Parenthesis,
    # sometimes grouping keywords/identifiers across a comma and breaking them up
    # within the same sub-clause, so we have to do some manual processing
    # to group tokens correctly.
    column_definition_groups = _split_column_identifiers_by_comma(column_identifiers)

    return reduce(_build_fields_metadata, column_definition_groups, {})


def _translate_create_table(
    statement: token_groups.Statement, table_token_idx: int
) -> typing.List[QueryExpression]:
    idx, table_identifier = statement.token_next_by(
        i=token_groups.Identifier, idx=table_token_idx
    )
    table_name = table_identifier.value

    idx, column_identifiers = statement.token_next_by(
        i=token_groups.Parenthesis, idx=idx
    )

    field_metadata = _extract_column_definitions(column_identifiers)
    create_collection = q.create_collection(
        {"name": table_name, "data": {"metadata": {"fields": field_metadata}}}
    )
    index_by_collection = partial(common.index_name, table_name)

    index_queries = [
        q.create_index(
            {
                "name": index_by_collection(index_type=common.IndexType.REF),
                "source": q.collection(table_name),
                "terms": [{"field": ["ref"]}],
            }
        ),
        q.create_index(
            {"name": index_by_collection(), "source": q.collection(table_name)}
        ),
    ]

    foreign_references = [
        field_name
        for field_name, field_data in field_metadata.items()
        if any(field_data["references"])
    ]

    for field_name, field_data in field_metadata.items():
        # Fauna can query documents by ID by default, so we don't need an index for it
        if field_name == "id":
            continue

        index_by_field = partial(index_by_collection, field_name)

        index_queries.extend(
            [
                q.create_index(
                    {
                        "name": index_by_field(common.IndexType.VALUE),
                        "source": q.collection(table_name),
                        "values": [{"field": ["data", field_name]}, {"field": ["ref"]}],
                    }
                ),
                # Sorting index, so we can support ORDER BY clauses in SQL queries.
                # This will allow us to order a set of refs by a value while still
                # keeping that same set of refs.
                q.create_index(
                    {
                        "name": index_by_field(common.IndexType.SORT),
                        "source": q.collection(table_name),
                        "terms": [{"field": ["ref"]}],
                        "values": [{"field": ["data", field_name]}, {"field": ["ref"]}],
                    }
                ),
            ]
        )

        # We need a separate index for unique fields, because the values-based indices
        # contain the 'ref' field, which will never be duplicated
        is_unique = field_data["unique"]
        if is_unique:
            index_queries.append(
                q.create_index(
                    {
                        "name": index_by_field(common.IndexType.TERM),
                        "source": q.collection(table_name),
                        "terms": [{"field": ["data", field_name]}],
                        "unique": is_unique,
                    }
                )
            )

        # We need a ref-based index for foreign keys to permit JOIN queries via matching
        # document refs
        is_foreign_key = any(field_data["references"])
        if is_foreign_key:
            index_queries.append(
                q.create_index(
                    {
                        "name": index_by_field(common.IndexType.REF),
                        "source": q.collection(table_name),
                        "terms": [{"field": ["data", field_name]}],
                    }
                )
            )
            # We create a foreign ref index per foreign ref that exists in the collection,
            # because this permits us to access any foreign ref we may need to continue
            # a chain of joins.
            for foreign_reference in foreign_references:
                index_queries.append(
                    q.create_index(
                        {
                            "name": index_by_field(
                                common.IndexType.REF, foreign_key_name=foreign_reference
                            ),
                            "source": q.collection(table_name),
                            "terms": [{"field": ["data", field_name]}],
                            "values": [
                                {"field": ["data", foreign_reference]},
                                {"field": ["ref"]},
                            ],
                        }
                    )
                )

    index_queries.append(
        q.let(
            {"collection": q.collection(table_name)},
            {"data": [{"id": q.var("collection")}]},
        )
    )
    # Fauna creates resources asynchronously, so we cannot create and use a collection
    # in the same transaction, so we have to run the expressions that create
    # the collection and the indices that depend on it separately
    return [create_collection, q.do(*index_queries)]


def _translate_create_index(
    statement: token_groups.Statement, idx: int
) -> typing.List[QueryExpression]:
    _, unique = statement.token_next_by(m=(token_types.Keyword, "UNIQUE"), idx=idx)
    idx, _ = statement.token_next_by(m=(token_types.Keyword, "ON"), idx=idx)
    _, index_params = statement.token_next_by(i=token_groups.Function, idx=idx)

    params_idx, table_identifier = index_params.token_next_by(i=token_groups.Identifier)
    table_name = table_identifier.value

    params_idx, column_identifiers = index_params.token_next_by(
        i=token_groups.Parenthesis, idx=params_idx
    )

    index_fields = [
        token.value
        for token in column_identifiers.flatten()
        if token.ttype == token_types.Name
    ]

    if len(index_fields) > 1:
        raise exceptions.NotSupportedError(
            "Creating indexes for multiple columns is not currently supported."
        )

    index_terms = [{"field": ["data", index_field]} for index_field in index_fields]
    index_name = common.index_name(
        table_name, column_name=index_fields[0], index_type=common.IndexType.TERM
    )

    return [
        q.do(
            q.if_(
                # We automatically create indices for some fields on collection creation,
                # so we can skip explicit index creation if it already exists.
                q.exists(q.index(index_name)),
                None,
                q.create_index(
                    {
                        "name": index_name,
                        "source": q.collection(table_name),
                        "terms": index_terms,
                        "unique": unique,
                    }
                ),
            ),
            q.let(
                {"collection": q.collection(table_name)},
                {"data": [{"id": q.var("collection")}]},
            ),
        )
    ]


def translate_create(statement: token_groups.Statement) -> typing.List[QueryExpression]:
    """Translate a CREATE SQL query into an equivalent FQL query.

    Params:
    -------
    statement: An SQL statement returned by sqlparse.

    Returns:
    --------
    An FQL query expression.
    """
    idx, keyword = statement.token_next_by(
        m=[(token_types.Keyword, "TABLE"), (token_types.Keyword, "INDEX")]
    )

    if keyword.value == "TABLE":
        return _translate_create_table(statement, idx)

    if keyword.value == "INDEX":
        return _translate_create_index(statement, idx)

    raise exceptions.NotSupportedError(
        "Only TABLE and INDEX are supported in CREATE statements."
    )
