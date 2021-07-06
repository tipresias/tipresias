"""Collection of objects representing RDB structures in SQL queries"""

from sqlparse import sql as token_groups


class Table:
    """Representation of a table object in SQL.

    Params:
    -------
    table_identifier: Parsed SQL Identifier for a table name.
    """

    def __init__(self, table_identifier: token_groups.Identifier):
        self.name = table_identifier.value
