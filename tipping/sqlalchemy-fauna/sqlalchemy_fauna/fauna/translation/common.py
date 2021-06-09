"""Shared SQL translations and utilities for various statement types."""

from typing import Union, Tuple, Sequence, Optional, cast
import re
from datetime import datetime, timezone
from warnings import warn
from dateutil import parser

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types


TableNames = Sequence[Optional[str]]
ColumnNames = Sequence[str]
Aliases = Sequence[Optional[str]]
IdentifierValues = Tuple[TableNames, ColumnNames, Aliases]


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
) -> Union[str, int, float, None, bool, datetime]:
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
    # Seems that mypy can't find the very real ParserError
    except (parser.ParserError, ValueError, _NumericString):  # type: ignore
        pass

    return string_value


def _parse_identifier(
    identifier: token_groups.Identifier,
) -> Tuple[Optional[str], str, Optional[str]]:
    idx, identifier_name = identifier.token_next_by(t=token_types.Name)

    tok_idx, next_token = identifier.token_next(idx, skip_ws=True)
    if next_token and next_token.match(token_types.Punctuation, "."):
        idx = tok_idx
        table_name = identifier_name.value
        idx, column_identifier = identifier.token_next_by(t=token_types.Name, idx=idx)
        column_name = column_identifier.value
    else:
        table_name = None
        column_name = identifier_name.value

    idx, as_keyword = identifier.token_next_by(m=(token_types.Keyword, "AS"), idx=idx)

    if as_keyword is not None:
        _, alias_identifier = identifier.token_next_by(
            i=token_groups.Identifier, idx=idx
        )
        alias_name = alias_identifier.value
    else:
        alias_name = None

    return (table_name, column_name, alias_name)


def parse_identifiers(
    identifiers: Union[token_groups.Identifier, token_groups.IdentifierList]
) -> IdentifierValues:
    """Extract raw table name, column name, and alias from SQL identifiers.

    Params:
    -------
    identifiers: Either a single identifier or identifier list.

    Returns:
    --------
    Tuple of table_names, column names, and column aliases.
    """
    if isinstance(identifiers, token_groups.Identifier):
        table_name, column_name, alias_name = _parse_identifier(identifiers)
        return ((table_name,), (column_name,), (alias_name,))

    return cast(
        IdentifierValues,
        tuple(
            zip(
                *[
                    _parse_identifier(identifier)
                    for identifier in identifiers
                    if isinstance(identifier, token_groups.Identifier)
                ]
            )
        ),
    )
