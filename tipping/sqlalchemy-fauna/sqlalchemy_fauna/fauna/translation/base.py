"""Public interface for the translation module."""

import typing

import sqlparse
from sqlparse import tokens as token_types
from sqlparse import sql as token_groups
from faunadb.objects import _Expr as QueryExpression
from toolz import functoolz, itertoolz

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


def _validate_sql(sql_statements: typing.Sequence[token_groups.Statement]):
    if len(sql_statements) > 1:
        raise exceptions.NotSupportedError(
            "Only one SQL statement at a time is currently supported. "
            f"The following query has more than one:\n{sql}"
        )

    return sql_statements


def _translate_ddl_statement(sql_statement: token_groups.Statement, ddl_keyword: str):
    if ddl_keyword == "CREATE":
        return translate_create(sql_statement)

    if ddl_keyword == "DROP":
        return translate_drop(sql_statement)

    if ddl_keyword == "ALTER":
        return translate_alter(sql_statement)

    raise exceptions.NotSupportedError()


def _translate_dml_statement(sql_statement: token_groups.Statement, dml_keyword: str):
    sql_query = sql.SQLQuery.from_statement(sql_statement)

    if dml_keyword == "SELECT":
        return [fql.translate_select(sql_query)]

    if dml_keyword == "INSERT":
        return [fql.translate_insert(sql_query)]

    if dml_keyword == "DELETE":
        return [fql.translate_delete(sql_query)]

    if dml_keyword == "UPDATE":
        return [fql.update_documents(sql_query)]

    raise exceptions.NotSupportedError()


def translate_sql_to_fql(
    sql_string: str,
) -> typing.List[QueryExpression]:
    """Translate from an SQL string to an FQL query

    Params:
    -------
    sql_string: A string that represents an SQL query.

    Returns:
    --------
    A list of FQL query expressions.
    """
    sql_statement = functoolz.pipe(
        sql_string, sqlparse.parse, _validate_sql, itertoolz.first
    )
    first_token = sql_statement.token_first()

    if first_token.ttype == token_types.DDL:
        return _translate_ddl_statement(sql_statement, first_token.value)

    if first_token.ttype == token_types.DML:
        return _translate_dml_statement(sql_statement, first_token.value)

    raise exceptions.NotSupportedError()
