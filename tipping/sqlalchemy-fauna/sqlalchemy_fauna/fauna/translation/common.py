"""Shared SQL translations and utilities for various statement types."""

import enum
import typing

from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q


NULL = "NULL"
DATA = "data"


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
        foreign_key_name is not None
        and column_name is not None
        and index_type == IndexType.REF
    )
    assert is_valid_foreign_key_name

    column_substring = "" if column_name is None else f"_by_{column_name}"
    index_type_substring = f"_{index_type.value}"
    foreign_key_substring = (
        "" if foreign_key_name is None else f"_to_{foreign_key_name}"
    )
    return table_name + column_substring + index_type_substring + foreign_key_substring
