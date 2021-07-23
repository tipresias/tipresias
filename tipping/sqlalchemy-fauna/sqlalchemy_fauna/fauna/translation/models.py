"""Collection of objects representing RDB structures in SQL queries"""

from __future__ import annotations

import typing
from functools import reduce

from sqlparse import sql as token_groups, tokens as token_types

from sqlalchemy_fauna import exceptions


# Probably not a complete list, but covers the basics
FUNCTION_NAMES = {"min", "max", "count", "avg", "sum"}


class Column:
    """Representation of a column object in SQL.

    Params:
    identifier: Parsed SQL Identifier for a column name and/or alias.
    """

    def __init__(self, identifier: token_groups.Identifier):
        self.name = ""
        self.alias = ""
        self._table: typing.Optional[Table] = None
        self._table_name: typing.Optional[str] = None

        idx = self._assign_names(identifier)
        self._assign_alias(identifier, idx)
        # Fauna doesn't have an 'id' field, so we extract the ID value from the 'ref' included
        # in query responses, but we still want to map the field name to aliases as with other
        # fields for consistency when passing results to SQLAlchemy
        if self.name == "id":
            self.name = "ref"

    @classmethod
    def from_identifier_group(
        cls,
        identifiers: typing.Union[
            token_groups.Identifier, token_groups.IdentifierList, token_groups.Function
        ],
    ) -> typing.List[Column]:
        """Create column objects from any of the possible SQL identifier objects.

        Params:
        -------
        identifiers: A parsed SQL token group that contains column names and/or aliases.

        Returns:
        --------
        A list of column objects.
        """
        if isinstance(identifiers, token_groups.IdentifierList):
            return [
                Column(id)
                for id in identifiers
                if isinstance(id, token_groups.Identifier)
            ]

        if isinstance(identifiers, token_groups.Function):
            _, identifier = identifiers.token_next_by(i=token_groups.Identifier)
            _, name = identifier.token_next_by(t=token_types.Name)

            if name.value.lower() in FUNCTION_NAMES:
                return [Column(token_groups.Identifier([identifiers]))]

            _, parenthesis = identifiers.token_next_by(i=token_groups.Parenthesis)
            _, column_id_list = parenthesis.token_next_by(i=token_groups.IdentifierList)
            columns = cls.from_identifier_group(column_id_list)
            for column in columns:
                column._table_name = name.value

            return columns

        if isinstance(identifiers, token_groups.Identifier):
            return [Column(identifiers)]

        raise exceptions.InternalError(
            f"Tried to create a column from unsupported SQL token type {type(identifiers)}"
        )

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

    @property
    def alias_map(self) -> typing.Dict[str, str]:
        """Dictionary that maps the column name to its alias in the SQL query."""
        return {self.name: self.alias}

    def _assign_names(self, identifier: token_groups.Identifier) -> int:
        idx, identifier_name = identifier.token_next_by(
            t=token_types.Name, i=token_groups.Function
        )

        tok_idx, next_token = identifier.token_next(idx, skip_ws=True)
        if next_token and next_token.match(token_types.Punctuation, "."):
            idx = tok_idx
            table_name = identifier_name.value
            idx, column_identifier = identifier.token_next_by(
                t=token_types.Name, idx=idx
            )
            column_name = column_identifier.value
        else:
            table_name = None
            column_name = identifier_name.value

        self.name = column_name
        self._table_name = table_name

        return idx

    def _assign_alias(self, identifier: token_groups.Identifier, idx: int):
        assert self.name is not None
        idx, as_keyword = identifier.token_next_by(
            m=(token_types.Keyword, "AS"), idx=idx
        )

        if as_keyword is None:
            self.alias = "id" if self.name == "ref" else self.name
        else:
            _, alias_identifier = identifier.token_next_by(
                i=token_groups.Identifier, idx=idx
            )
            self.alias = alias_identifier.value

    def __str__(self) -> str:
        return self.name


class Table:
    """Representation of a table object in SQL.

    Params:
    -------
    name: Name of the table.
    columns: Column objects that belong to the given table.
    """

    def __init__(self, name: str, columns: typing.Optional[typing.List[Column]] = None):
        self.name = name
        self._columns: typing.List[Column] = []

        columns = columns or []
        for column in columns:
            self.add_column(column)

    @classmethod
    def from_identifier(cls, identifier: token_groups.Identifier) -> Table:
        """Extract table name from an SQL identifier.

        Params:
        -------
        identifier: SQL token that contains the table's name.

        Returns:
        --------
        A new Table object.
        """
        name = identifier.value
        return cls(name=name)

    @property
    def columns(self) -> typing.List[Column]:
        """List of column objects associated with this table."""
        return self._columns

    def add_column(self, column: Column):
        """Add an associated column object to this table."""
        assert self.name is not None

        matching_column = (col for col in self.columns if column.name == col.name)
        try:
            next(matching_column)
        except StopIteration:
            column.table = self
            self._columns.append(column)

    @property
    def column_alias_map(self) -> typing.Dict[str, str]:
        """Dictionary that maps column names to their aliases in the SQL query."""
        collect_alias_maps = lambda acc, col: {**acc, **col.alias_map}
        return reduce(collect_alias_maps, self.columns, {})

    def __str__(self) -> str:
        return self.name
