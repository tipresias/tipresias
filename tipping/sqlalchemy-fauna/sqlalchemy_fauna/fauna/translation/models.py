"""Collection of objects representing RDB structures in SQL queries"""

from __future__ import annotations

import typing
from functools import reduce

from sqlparse import sql as token_groups, tokens as token_types
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions


ColumnParams = TypedDict(
    "ColumnParams", {"table_name": typing.Optional[str], "name": str, "alias": str}
)

# Probably not a complete list, but covers the basics
FUNCTION_NAMES = {"min", "max", "count", "avg", "sum"}


class Column:
    """Representation of a column object in SQL.

    Params:
    identifier: Parsed SQL Identifier for a column name and/or alias.
    """

    def __init__(self, table_name: typing.Optional[str], name: str, alias: str):
        self.name = name
        self.alias = alias
        self._table_name = table_name
        self._table: typing.Optional[Table] = None

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
                Column.from_identifier(id)
                for id in identifiers
                if isinstance(id, token_groups.Identifier)
            ]

        if isinstance(identifiers, token_groups.Function):
            _, identifier = identifiers.token_next_by(i=token_groups.Identifier)
            _, name = identifier.token_next_by(t=token_types.Name)

            if name.value.lower() in FUNCTION_NAMES:
                return [Column.from_identifier(token_groups.Identifier([identifiers]))]

            _, parenthesis = identifiers.token_next_by(i=token_groups.Parenthesis)
            _, column_id_list = parenthesis.token_next_by(i=token_groups.IdentifierList)
            columns = cls.from_identifier_group(column_id_list)
            for column in columns:
                column._table_name = name.value

            return columns

        if isinstance(identifiers, token_groups.Identifier):
            return [Column.from_identifier(identifiers)]

        raise exceptions.InternalError(
            f"Tried to create a column from unsupported SQL token type {type(identifiers)}"
        )

    @classmethod
    def from_identifier(cls, identifier: token_groups.Identifier) -> Column:
        """Create a column from an SQL identifier token.

        Params:
        -------
        identifier: SQL token with column label.

        Returns:
        --------
        A Column object based on the given identifier token.
        """
        idx, identifier_name = identifier.token_next_by(
            t=token_types.Name, i=token_groups.Function
        )

        _, maybe_dot = identifier.token_next(idx, skip_ws=True, skip_cm=True)
        if maybe_dot is None or not maybe_dot.match(token_types.Punctuation, "."):
            table_name = None
            name = identifier_name.value
        else:
            table_name = identifier_name.value
            idx, column_name_token = identifier.token_next_by(
                t=token_types.Name, idx=idx
            )
            # Fauna doesn't have an 'id' field, so we extract the ID value from the 'ref' included
            # in query responses, but we still want to map the field name to aliases as with other
            # fields for consistency when passing results to SQLAlchemy
            name = "ref" if column_name_token.value == "id" else column_name_token.value

        idx, as_keyword = identifier.token_next_by(
            m=(token_types.Keyword, "AS"), idx=idx
        )

        if as_keyword is None:
            alias = "id" if name == "ref" else name
        else:
            _, alias_identifier = identifier.token_next_by(
                i=token_groups.Identifier, idx=idx
            )
            alias = alias_identifier.value

        column_params: ColumnParams = {
            "table_name": table_name,
            "name": name,
            "alias": alias,
        }

        return Column(**column_params)

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


class SQLQuery:
    """Representation of an entire SQL query statement.

    Params:
    -------
    tables: List of tables referenced in the query.
    """

    def __init__(self, tables: typing.List[Table]):
        self._tables = tables

    @classmethod
    def from_statement(cls, statement: token_groups.Statement) -> SQLQuery:
        """Extract an SQLQuery object from an SQL statement token.

        Params:
        -------
        statement: SQL token that contains the entire query.

        Returns:
        --------
        A new SQLQuery object.
        """
        first_token = statement.token_first(skip_cm=True, skip_ws=True)

        if first_token.match(token_types.DML, "SELECT"):
            return cls._build_select_query(statement)

        if first_token.match(token_types.DML, "UPDATE"):
            return cls._build_update_query(statement)

        if first_token.match(token_types.DML, "INSERT"):
            return cls._build_insert_query(statement)

        if first_token.match(token_types.DML, "DELETE"):
            return cls._build_delete_query(statement)

        raise exceptions.NotSupportedError(f"Unsupported query type {first_token}")

    @classmethod
    def _build_select_query(cls, statement: token_groups.Statement) -> SQLQuery:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "FROM"))
        _, table_identifier = statement.token_next_by(
            i=(token_groups.Identifier), idx=idx
        )

        # If we can't find a single table identifier, it means that multiple tables
        # are referenced in the FROM clause, which isn't supported.
        if table_identifier is None:
            raise exceptions.NotSupportedError(
                "Only one table per query is currently supported"
            )

        table = Table.from_identifier(table_identifier)

        _, wildcard = statement.token_next_by(t=(token_types.Wildcard))

        if wildcard is not None:
            raise exceptions.NotSupportedError("Wildcards ('*') are not yet supported")

        idx, identifiers = statement.token_next_by(
            i=(
                token_groups.Identifier,
                token_groups.IdentifierList,
                token_groups.Function,
            )
        )

        for column in Column.from_identifier_group(identifiers):
            table.add_column(column)

        return cls(tables=[table])

    @classmethod
    def _build_update_query(cls, statement: token_groups.Statement) -> SQLQuery:
        idx, table_identifier = statement.token_next_by(i=token_groups.Identifier)

        if table_identifier is None:
            raise exceptions.NotSupportedError(
                "Only one table per query is currently supported"
            )

        table = Table.from_identifier(table_identifier)

        idx, _ = statement.token_next_by(m=(token_types.Keyword, "SET"), idx=idx)
        idx, comparison_group = statement.token_next_by(
            i=token_groups.Comparison, idx=idx
        )

        _, update_column = comparison_group.token_next_by(i=token_groups.Identifier)
        column = Column.from_identifier(update_column)
        table.add_column(column)

        return cls(tables=[table])

    @classmethod
    def _build_insert_query(cls, statement: token_groups.Statement) -> SQLQuery:
        _, function_group = statement.token_next_by(i=token_groups.Function)

        if function_group is None:
            raise exceptions.NotSupportedError(
                "INSERT INTO statements without column names are not currently supported."
            )

        func_idx, table_identifier = function_group.token_next_by(
            i=token_groups.Identifier
        )
        table = Table.from_identifier(table_identifier)

        _, column_group = function_group.token_next_by(
            i=token_groups.Parenthesis, idx=func_idx
        )
        _, column_identifiers = column_group.token_next_by(
            i=(token_groups.IdentifierList, token_groups.Identifier)
        )

        for column in Column.from_identifier_group(column_identifiers):
            table.add_column(column)

        return cls(tables=[table])

    @classmethod
    def _build_delete_query(cls, statement: token_groups.Statement) -> SQLQuery:
        _, table_identifier = statement.token_next_by(i=token_groups.Identifier)
        table = Table.from_identifier(table_identifier)

        return cls(tables=[table])

    @property
    def tables(self):
        """List of data tables referenced in the SQL query."""
        return self._tables
