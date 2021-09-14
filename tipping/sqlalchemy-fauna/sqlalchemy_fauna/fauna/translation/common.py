"""Shared SQL translations and utilities for various statement types."""

import enum
import typing
import re
from datetime import datetime, timezone
from warnings import warn
from dateutil import parser

from sqlparse import sql as token_groups
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q


NULL = "NULL"
DATA = "data"


class _NumericString(Exception):
    pass


class IndexType(enum.Enum):
    """Enum for the different types of Fauna indices used."""

    ALL = "all"
    REF = "ref"
    TERM = "term"
    VALUE = "value"
    SORT = "sort"


def _parse_date_value(value):
    try:
        int(value)
        float(value)
        raise _NumericString()
    except ValueError:
        pass

    # We use isoparse instaed of parse, because the latter is too flexible
    # and will parse strings that aren't intended as datetime. Datetime strings
    # should always be in ISO format, because that's how we clean them in the dbapi.
    date_value = parser.isoparse(value)

    if date_value.tzinfo is None:
        warn(
            "Received a timezone-naive datetime value. Fauna only supports "
            "UTC timestamps, so converting to UTC."
        )
        return date_value.replace(tzinfo=timezone.utc)

    return date_value.astimezone(timezone.utc)


def extract_value(
    token: token_groups.Token,
) -> typing.Union[str, int, float, None, bool, datetime]:
    """ "Get the raw value from an SQL token.

    Params:
    -------
    token: An SQL token created by sqlparse.

    Returns:
    --------
    Raw token value of the relevant Python data type.
    """
    value = token.value

    if value.upper() == "NONE" or value.upper() == "NULL":
        return None

    if value.upper() == "TRUE":
        return True

    if value.upper() == "FALSE":
        return False

    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass

    try:
        return int(value)
    except ValueError:
        pass

    # sqlparse leaves ' characters around string values in the SQL, so we strip them out.
    string_value = re.sub("^'|'$", "", value)

    try:
        return _parse_date_value(string_value)
    except (parser.ParserError, ValueError, _NumericString):
        pass

    return string_value


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
