"""Collection of objects representing RDB structures in SQL queries"""

from __future__ import annotations

import typing

from sqlparse import sql as token_groups
from sqlparse import tokens as token_types


class Column:
    """Representation of a column object in SQL.

    Params:
    identifier: Parsed SQL Identifier for a column name and/or alias.
    """

    def __init__(self, identifier: token_groups.Identifier):
        self._table: typing.Optional[Table] = None
        self._table_name: typing.Optional[str] = None
        idx = self._assign_names(identifier)
        self._assign_alias(identifier, idx)

    @property
    def table(self) -> typing.Optional[Table]:
        """Table object associated with this column."""
        return self._table

    @table.setter
    def table(self, table: Table):
        assert self._table_name is None or self._table_name == table.name

        self._table = table
        self._table_name = table.name

    @property
    def table_name(self) -> typing.Optional[str]:
        """Name of the associated table in the SQL query."""
        return self._table_name

    def _assign_names(self, identifier: token_groups.Identifier) -> int:
        idx, identifier_name = identifier.token_next_by(
            t=token_types.Name, i=token_groups.Function
        )

        maybe_idx, next_token = identifier.token_next(idx, skip_ws=True)
        if next_token and next_token.match(token_types.Punctuation, "."):
            idx = maybe_idx
            self._table_name = identifier_name.value

            idx, column_identifier = identifier.token_next_by(
                t=token_types.Name, idx=idx
            )
            self.name = column_identifier.value
        else:
            self._table_name = None
            self.name = identifier_name.value

        return idx

    def _assign_alias(self, identifier: token_groups.Identifier, idx: int):
        idx, as_keyword = identifier.token_next_by(
            m=(token_types.Keyword, "AS"), idx=idx
        )

        if as_keyword is None:
            self.alias = None
        else:
            _, alias_identifier = identifier.token_next_by(
                i=token_groups.Identifier, idx=idx
            )
            self.alias = alias_identifier.value


class Table:
    """Representation of a table object in SQL.

    Params:
    -------
    identifier: Parsed SQL Identifier for a table name.
    columns: Column objects that belong to the given table.
    """

    def __init__(
        self,
        identifier: token_groups.Identifier,
        columns: typing.Optional[typing.List[Column]] = None,
    ):
        self.name = identifier.value
        self._columns: typing.List[Column] = []

        columns = columns or []
        for column in columns:
            self.add_column(column)

    @property
    def columns(self) -> typing.List[Column]:
        """List of column objects associated with this table."""
        return self._columns

    def add_column(self, column: Column):
        """Add an associated column object to this table."""
        assert self.name is not None

        column.table = self
        self._columns.append(column)
