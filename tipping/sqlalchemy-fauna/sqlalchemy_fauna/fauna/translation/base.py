"""Public interface for the translation module."""

import typing

import sqlparse
from sqlparse import tokens as token_types
from faunadb.objects import _Expr as QueryExpression

from sqlalchemy_fauna import exceptions, sql
from .. import fql
from .create import translate_create
from .drop import translate_drop
from .alter import translate_alter


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
    sql_string: str,
) -> typing.List[QueryExpression]:
    """Translate from an SQL string to an FQL query"""
    sql_statements = sqlparse.parse(sql_string)

    if len(sql_statements) > 1:
        raise exceptions.NotSupportedError(
            "Only one SQL statement at a time is currently supported. "
            f"The following query has more than one:\n{sql_string}"
        )

    sql_statement = sql_statements[0]

    if sql_statement.token_first().match(token_types.DDL, "CREATE"):
        return translate_create(sql_statement)

    if sql_statement.token_first().match(token_types.DDL, "DROP"):
        return translate_drop(sql_statement)

    if sql_statement.token_first().match(token_types.DDL, "ALTER"):
        return translate_alter(sql_statement)

    if sql_statement.token_first().match(token_types.DML, "SELECT"):
        sql_query = sql.SQLQuery.from_statement(sql_statement)
        return [fql.translate_select(sql_query)]

    if sql_statement.token_first().match(token_types.DML, "INSERT"):
        sql_query = sql.SQLQuery.from_statement(sql_statement)
        return [fql.translate_insert(sql_query)]

    if sql_statement.token_first().match(token_types.DML, "DELETE"):
        sql_query = sql.SQLQuery.from_statement(sql_statement)
        return [fql.translate_delete(sql_query)]

    if sql_statement.token_first().match(token_types.DML, "UPDATE"):
        sql_query = sql.SQLQuery.from_statement(sql_statement)
        table = sql_query.tables[0]
        return [fql.update_documents(table)]

    raise exceptions.NotSupportedError()
