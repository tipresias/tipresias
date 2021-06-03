"""Translate from an SQL string to an FQL query"""

import sqlparse


def format_sql_query(sql_query: str) -> str:
    """Format an SQL string for better readability.

    Params:
    ------
    sql_query: SQL string to format.
    """
    return sqlparse.format(
        sql_query, keyword_case="upper", strip_comments=True, reindent=True
    )
