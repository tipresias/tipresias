"""Shared SQL translations and utilities for various statement types."""

import typing
import re
from datetime import datetime, timezone
from warnings import warn
from dateutil import parser

from sqlparse import sql as token_groups
from mypy_extensions import TypedDict
from faunadb.objects import _Expr as QueryExpression
from faunadb import query as q

TableNames = typing.Sequence[typing.Optional[str]]
ColumnNames = typing.Sequence[str]
Aliases = typing.Sequence[typing.Optional[str]]
IdentifierValues = typing.Tuple[TableNames, ColumnNames, Aliases]

IndexComparison = typing.Tuple[str, typing.Union[int, float, str, None, bool, datetime]]
Comparisons = TypedDict(
    "Comparisons",
    {
        "by_id": typing.Optional[typing.Union[int, str]],
        "by_index": typing.List[IndexComparison],
    },
)

FieldAliasMap = typing.Dict[str, str]
TableFieldMap = typing.Dict[typing.Optional[str], FieldAliasMap]


NULL = "NULL"
DATA = "data"


class _NumericString(Exception):
    pass


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

    if value.upper() == "NONE":
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
    references: QueryExpression,
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
            # Assumes that there is only one reference per foreign key
            # and that it refers to the associated collection's ID field
            # (e.g. {'associated_table': 'id'}).
            # This is enforced via NotSupported errors when creating collections.
            "references": q.union(q.to_array(references)),
            "reference_collection": q.select(0, q.var("references"), default=NULL),
            "is_blank_reference": q.or_(
                q.is_null(foreign_value),
                q.equals(foreign_value, NULL),
                q.equals(q.var("reference_collection"), NULL),
            ),
        },
        q.if_(
            q.var("is_blank_reference"),
            None,
            q.ref(q.collection(q.var("reference_collection")), foreign_value),
        ),
    )
