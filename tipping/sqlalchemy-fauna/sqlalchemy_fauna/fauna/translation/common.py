"""Shared SQL translations and utilities for various statement types."""

from typing import Union
import re

from sqlparse import sql as token_groups


def extract_value(token: token_groups.Token) -> Union[str, int, float, None, bool]:
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
    return re.sub("^'|'$", "", value)
