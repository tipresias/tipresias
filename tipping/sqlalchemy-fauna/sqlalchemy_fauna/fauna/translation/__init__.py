"""Translate an SQL query into an equivalent FQL query"""

from typing import Union, List

import sqlparse
from sqlparse import tokens as token_types
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions
from .select import translate_select
from .create import translate_create
from .drop import translate_drop
from .insert import translate_insert
from .delete import translate_delete
from .update import translate_update


def format_sql_query(sql_query: str) -> str:
    """Format an SQL string for better readability.

    Params:
    ------
    sql_query: SQL string to format.
    """
    return sqlparse.format(
        sql_query, keyword_case="upper", strip_comments=True, reindent=True
    )


def translate_sql_to_fql(
    sql_query: str,
) -> Union[QueryExpression, List[QueryExpression]]:
    """Translate from an SQL string to an FQL query"""
    sql_statements = sqlparse.parse(sql_query)

    if len(sql_statements) > 1:
        raise exceptions.NotSupportedError(
            "Only one SQL statement at a time is currently supported. "
            f"The following query has more than one:\n{sql_query}"
        )

    sql_statement = sql_statements[0]

    if sql_statement.token_first().match(token_types.DML, "SELECT"):
        return translate_select(sql_statement)

    if sql_statement.token_first().match(token_types.DDL, "CREATE"):
        return translate_create(sql_statement)

    if sql_statement.token_first().match(token_types.DDL, "DROP"):
        return translate_drop(sql_statement)

    if sql_statement.token_first().match(token_types.DML, "INSERT"):
        return translate_insert(sql_statement)

    if sql_statement.token_first().match(token_types.DML, "DELETE"):
        return translate_delete(sql_statement)

    if sql_statement.token_first().match(token_types.DML, "UPDATE"):
        return translate_update(sql_statement)

    raise exceptions.NotSupportedError()
