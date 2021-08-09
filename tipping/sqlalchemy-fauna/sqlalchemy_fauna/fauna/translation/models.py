"""Collection of objects representing RDB structures in SQL queries"""

from __future__ import annotations
import functools

import typing
from functools import reduce
from datetime import datetime
import enum

from sqlparse import sql as token_groups, tokens as token_types
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions
from .common import extract_value


ColumnParams = TypedDict(
    "ColumnParams", {"table_name": typing.Optional[str], "name": str, "alias": str}
)


class JoinDirection(enum.Enum):
    """Enum for table join directions."""

    LEFT = "left"
    RIGHT = "right"


# Probably not a complete list, but covers the basics
FUNCTION_NAMES = {"min", "max", "count", "avg", "sum"}
GREATER_THAN = ">"
LESS_THAN = "<"

REVERSE_JOIN = {
    JoinDirection.LEFT: JoinDirection.RIGHT,
    JoinDirection.RIGHT: JoinDirection.LEFT,
}


class Column:
    """Representation of a column object in SQL.

    Params:
    identifier: Parsed SQL Identifier for a column name and/or alias.
    """

    def __init__(self, name: str, alias: str, table_name: typing.Optional[str] = None):
        self.name = name
        self.alias = alias
        self._table_name = table_name
        self._table: typing.Optional[Table] = None

    @classmethod
    def from_identifier_group(
        cls,
        identifiers: typing.Union[
            token_groups.Identifier,
            token_groups.IdentifierList,
            token_groups.Function,
            token_groups.Comparison,
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
        if isinstance(
            identifiers, (token_groups.IdentifierList, token_groups.Comparison)
        ):
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


class Filter:
    """Representation of filter applied by WHERE clause in SQL.

    Params:
    -------
    column: An instance of the Column used in the filter.
    operator: The comparison operator.
    value: The raw value being compared for the filter.
    """

    SUPPORTED_COMPARISON_OPERATORS = ["=", GREATER_THAN, ">=", "<", "<="]

    def __init__(
        self,
        column: Column,
        operator: str,
        value: typing.Union[str, int, float, None, bool, datetime],
    ):
        self.column = column
        self.operator = operator
        self.value = value
        self._table: typing.Optional[Table] = None
        self._table_name = column.table_name

    @classmethod
    def from_where_group(cls, where_group: token_groups.Where) -> typing.List[Filter]:
        """Parse a WHERE token to extract all filters contained therein.

        Params:
        -------
        where_group: A Where SQL token from sqlparse.

        Returns:
        --------
        A list of Filter instances based on all conditions contained
            within the WHERE clause.
        """
        if where_group is None:
            return []

        _, or_keyword = where_group.token_next_by(m=(token_types.Keyword, "OR"))
        if or_keyword is not None:
            raise exceptions.NotSupportedError("OR not yet supported in WHERE clauses.")

        _, between_keyword = where_group.token_next_by(
            m=(token_types.Keyword, "BETWEEN")
        )
        if between_keyword is not None:
            raise exceptions.NotSupportedError(
                "BETWEEN not yet supported in WHERE clauses."
            )

        where_filters = []
        idx = 0

        while True:
            idx, comparison = where_group.token_next_by(
                i=(token_groups.Comparison, token_groups.Identifier), idx=idx
            )
            if comparison is None:
                break

            if isinstance(comparison, token_groups.Identifier):
                where_filter = cls._parse_is_null(where_group, idx=idx)
            else:
                where_filter = cls._parse_comparison(comparison)

            where_filters.append(where_filter)

            idx, _ = where_group.token_next_by(m=(token_types.Keyword, "AND"), idx=idx)
            if idx is None:
                break

        return where_filters

    @classmethod
    def _parse_is_null(cls, where_group: token_groups.Where, idx) -> Filter:
        idx, identifier = where_group.token_next(idx - 1)

        idx, is_kw = where_group.token_next(idx, skip_cm=True, skip_ws=True)
        assert is_kw and is_kw.match(token_types.Keyword, "IS")

        _, null_kw = where_group.token_next(idx, skip_ws=True, skip_cm=True)
        assert null_kw and null_kw.match(token_types.Keyword, "NULL")

        columns = Column.from_identifier_group(identifier)
        assert len(columns) == 1
        column = columns[0]

        return cls(column=column, operator="=", value=None)

    @classmethod
    def _parse_comparison(cls, comparison_group: token_groups.Comparison) -> Filter:
        id_idx, comparison_identifier = comparison_group.token_next_by(
            i=token_groups.Identifier
        )
        columns = Column.from_identifier_group(comparison_identifier)
        assert len(columns) == 1
        column = columns[0]

        _, comparison_operator = comparison_group.token_next_by(
            t=token_types.Comparison
        )

        if comparison_operator.value not in cls.SUPPORTED_COMPARISON_OPERATORS:
            raise exceptions.NotSupportedError(
                "Only the following comparisons are supported in WHERE clauses: "
                ", ".join(cls.SUPPORTED_COMPARISON_OPERATORS)
            )

        value_idx, comparison_value_literal = comparison_group.token_next_by(
            t=token_types.Literal
        )
        comparison_value = extract_value(comparison_value_literal)
        operator_value = cls._extract_operator_value(
            comparison_operator.value, id_idx, value_idx
        )

        return Filter(column=column, operator=operator_value, value=comparison_value)

    @classmethod
    def _extract_operator_value(
        cls, operator_value: str, id_idx: int, value_idx: int
    ) -> str:
        # We're enforcing the convention of <column name> <operator> <value> for WHERE
        # clauses here to simplify later query translation.
        # Unfortunately, FQL generation depends on this convention without that dependency
        # being explicit, which increases the likelihood of future bugs. However, I can't
        # think of a good way to centralize the knowledge of this convention across all
        # query translation, so I'm leaving this note as a warning.
        identifier_comes_before_value = id_idx < value_idx
        if identifier_comes_before_value:
            return operator_value

        if GREATER_THAN in operator_value:
            return operator_value.replace(GREATER_THAN, LESS_THAN)

        if LESS_THAN in operator_value:
            return operator_value.replace(LESS_THAN, GREATER_THAN)

        return operator_value

    @property
    def table(self) -> typing.Optional[Table]:
        """Table object associated with this column."""
        return self._table

    @table.setter
    def table(self, table: Table):
        assert self._table_name in (None, table.name)

        self._table = table
        self._table_name = table.name

    @property
    def table_name(self) -> typing.Optional[str]:
        """Name of the associated table in the SQL query."""
        return self._table_name


class Table:
    """Representation of a table object in SQL.

    Params:
    -------
    name: Name of the table.
    columns: Column objects that belong to the given table.
    """

    def __init__(
        self,
        name: str,
        columns: typing.Optional[typing.List[Column]] = None,
        filters: typing.Optional[typing.List[Filter]] = None,
    ):
        self.name = name
        self._columns: typing.List[Column] = []
        self._filters: typing.List[Filter] = []
        self.left_join_table: typing.Optional[Table] = None
        self.left_join_key: typing.Optional[Column] = None
        self.right_join_table: typing.Optional[Table] = None
        self.right_join_key: typing.Optional[Column] = None

        columns = columns or []
        for column in columns:
            self.add_column(column)

        filters = filters or []
        for sql_filter in filters:
            self.add_filter(sql_filter)

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
    def filters(self) -> typing.List[Filter]:
        """List of filter objects associated with this table."""
        return self._filters

    def add_filter(self, sql_filter: Filter):
        """Add an associated column object to this table."""
        assert self.name is not None

        sql_filter.table = self
        self._filters.append(sql_filter)

    def add_join(
        self,
        foreign_table: Table,
        comparison_group: token_groups.Comparison,
        direction: JoinDirection,
    ):
        """Add a foreign reference via join."""
        setattr(self, f"{direction.value}_join_table", foreign_table)
        setattr(foreign_table, f"{REVERSE_JOIN[direction].value}_join_table", self)

        join_columns = Column.from_identifier_group(comparison_group)
        join_on_id = functools.reduce(
            lambda has_id, column: has_id or column.name == "ref", join_columns, False
        )

        if not join_on_id:
            raise exceptions.NotSupportedError(
                "Table joins are only permitted on IDs and foreign keys "
                f"that refer to IDs, but tried to join on {comparison_group.value}."
            )

        join_key = next(
            join_column
            for join_column in join_columns
            if join_column.table_name == self.name
        )
        setattr(self, f"{direction.value}_join_key", join_key)

        foreign_join_key = next(
            join_column
            for join_column in join_columns
            if join_column.table_name == foreign_table.name
        )
        setattr(
            foreign_table,
            f"{REVERSE_JOIN[direction].value}_join_key",
            foreign_join_key,
        )

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

    def __init__(
        self,
        tables: typing.List[Table] = None,
        columns: typing.List[Column] = None,
        distinct: bool = False,
    ):
        self.distinct = distinct
        tables = tables or []
        self._tables = tables
        columns = columns or []
        self._columns = columns

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
        tables = cls._collect_tables(statement)

        if first_token.match(token_types.DML, "SELECT"):
            sql_instance = cls._build_select_query(statement, tables)

        if first_token.match(token_types.DML, "UPDATE"):
            assert len(tables) == 1
            table = tables[0]
            sql_instance = cls._build_update_query(statement, table)

        if first_token.match(token_types.DML, "INSERT"):
            assert len(tables) == 1
            table = tables[0]
            sql_instance = cls._build_insert_query(statement, table)

        if first_token.match(token_types.DML, "DELETE"):
            assert len(tables) == 1
            table = tables[0]
            sql_instance = cls._build_delete_query(table)

        if sql_instance is None:
            raise exceptions.NotSupportedError(f"Unsupported query type {first_token}")

        _, where_group = statement.token_next_by(i=(token_groups.Where))
        for where_filter in Filter.from_where_group(where_group):
            sql_instance.add_filter_to_table(where_filter)

        return sql_instance

    @classmethod
    def _collect_tables(cls, statement: token_groups.Statement) -> typing.List[Table]:
        idx, _ = statement.token_next_by(
            m=[
                (token_types.Keyword, "FROM"),
                (token_types.Keyword, "INTO"),
                (token_types.DML, "UPDATE"),
            ]
        )
        _, maybe_table_identifier = statement.token_next(
            idx=idx, skip_cm=True, skip_ws=True
        )

        if isinstance(maybe_table_identifier, token_groups.Function):
            maybe_table_identifier = maybe_table_identifier.token_first(
                skip_cm=True, skip_ws=True
            )

        # If we can't find a single table identifier, it means that multiple tables
        # are referenced in the FROM/INTO clause, which isn't supported.
        if not isinstance(maybe_table_identifier, token_groups.Identifier):
            raise exceptions.NotSupportedError(
                "In order to query multiple tables at a time, you must join them "
                "together with a JOIN clause."
            )

        table_identifier = maybe_table_identifier
        tables = [Table.from_identifier(table_identifier)]

        while True:
            idx, join_kw = statement.token_next_by(
                m=(token_types.Keyword, "JOIN"), idx=idx
            )
            if join_kw is None:
                break

            idx, table_identifier = statement.token_next(
                idx, skip_ws=True, skip_cm=True
            )
            table = Table.from_identifier(table_identifier)

            idx, comparison_group = statement.token_next_by(
                i=token_groups.Comparison, idx=idx
            )

            table.add_join(tables[-1], comparison_group, JoinDirection.LEFT)
            tables.append(table)

        return tables

    @classmethod
    def _build_select_query(
        cls, statement: token_groups.Statement, tables: typing.List[Table]
    ) -> SQLQuery:
        _, wildcard = statement.token_next_by(t=(token_types.Wildcard))

        if wildcard is not None:
            raise exceptions.NotSupportedError("Wildcards ('*') are not yet supported")

        _, identifiers = statement.token_next_by(
            i=(
                token_groups.Identifier,
                token_groups.IdentifierList,
                token_groups.Function,
            )
        )
        columns = []

        for column in Column.from_identifier_group(identifiers):
            try:
                table = next(
                    table for table in tables if table.name == column.table_name
                )
            except StopIteration:
                table = tables[0]

            columns.append(column)
            table.add_column(column)

        _, distinct = statement.token_next_by(m=(token_types.Keyword, "DISTINCT"))

        return cls(tables=tables, columns=columns, distinct=bool(distinct))

    @classmethod
    def _build_update_query(
        cls, statement: token_groups.Statement, table: Table
    ) -> SQLQuery:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "SET"))
        idx, comparison_group = statement.token_next_by(
            i=token_groups.Comparison, idx=idx
        )

        _, update_column = comparison_group.token_next_by(i=token_groups.Identifier)
        column = Column.from_identifier(update_column)
        table.add_column(column)

        return cls(tables=[table], columns=[column])

    @classmethod
    def _build_insert_query(
        cls, statement: token_groups.Statement, table: Table
    ) -> SQLQuery:
        _, function_group = statement.token_next_by(i=token_groups.Function)

        if function_group is None:
            raise exceptions.NotSupportedError(
                "INSERT INTO statements without column names are not currently supported."
            )

        _, column_group = function_group.token_next_by(i=token_groups.Parenthesis)
        _, column_identifiers = column_group.token_next_by(
            i=(token_groups.IdentifierList, token_groups.Identifier)
        )
        columns = []

        for column in Column.from_identifier_group(column_identifiers):
            columns.append(column)
            table.add_column(column)

        return cls(tables=[table], columns=columns)

    @classmethod
    def _build_delete_query(cls, table: Table) -> SQLQuery:
        return cls(tables=[table])

    @property
    def tables(self):
        """List of data tables referenced in the SQL query."""
        return self._tables

    @property
    def columns(self):
        """List of columns referenced in the SQL query in the order that they appear."""
        return self._columns

    def add_filter_to_table(self, sql_filter: Filter):
        """Associates the given Filter with the Table that it applies to.

        Params:
        -------
        sql_filter: An instance of Filter.
        """
        try:
            table = next(
                table for table in self.tables if table.name == sql_filter.table_name
            )
        except StopIteration:
            raise exceptions.Error(  # pylint: disable=raise-missing-from
                f"Didn't find table '{sql_filter.table_name}' in queried tables."
            )

        table.add_filter(sql_filter)
