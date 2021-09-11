"""Collection of objects representing RDB structures in SQL queries"""

from __future__ import annotations
import functools
import itertools
import typing
from datetime import datetime
import enum
import re

from sqlparse import sql as token_groups, tokens as token_types
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions
from .common import extract_value


class JoinDirection(enum.Enum):
    """Enum for table join directions."""

    LEFT = "left"
    RIGHT = "right"


class OrderDirection(enum.Enum):
    """Enum for direction of results ordering."""

    ASC = "ASC"
    DESC = "DESC"


class Function(enum.Enum):
    """Enum for identifying SQL functions."""

    COUNT = "COUNT"


ColumnParams = TypedDict(
    "ColumnParams",
    {
        "table_name": typing.Optional[str],
        "name": str,
        "alias": str,
        "function_name": typing.Optional[Function],
    },
)


# Probably not a complete list, but covers the basics
FUNCTION_NAMES = {"min", "max", "count", "avg", "sum"}
GREATER_THAN = ">"
LESS_THAN = "<"

REVERSE_JOIN = {
    JoinDirection.LEFT: JoinDirection.RIGHT,
    JoinDirection.RIGHT: JoinDirection.LEFT,
}

NOT_SUPPORTED_FUNCTION_REGEX = re.compile(r"^(?:MIN|MAX|AVG|SUM)\(.+\)$", re.IGNORECASE)
COUNT_REGEX = re.compile(r"^COUNT\(.+\)$", re.IGNORECASE)


class Column:
    """Representation of a column object in SQL.

    Params:
    identifier: Parsed SQL Identifier for a column name and/or alias.
    """

    def __init__(
        self,
        name: str,
        alias: str,
        table_name: typing.Optional[str] = None,
        value: typing.Optional[typing.Union[str, int, float, datetime]] = None,
        function_name: typing.Optional[Function] = None,
    ):
        self.name = name
        self.alias = alias
        self.value = value
        self.function_name = function_name
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

        function_name: typing.Optional[Function] = None
        if re.match(COUNT_REGEX, name):
            function_name = Function.COUNT
        elif re.match(NOT_SUPPORTED_FUNCTION_REGEX, name):
            raise exceptions.NotSupportedError(
                "MIN, MAX, AVG, and SUM functions are not yet supported."
            )

        column_params: ColumnParams = {
            "table_name": table_name,
            "name": name,
            "alias": alias,
            "function_name": function_name,
        }

        return Column(**column_params)

    @classmethod
    def from_comparison_group(cls, comparison_group: token_groups.Comparison) -> Column:
        """Create a column from a Comparison group token.

        Params:
        -------
        comparison_group: Token group that contains the column identifier and updated value.

        Returns:
        --------
        A column object with the value attribute.
        """
        _, column_identifier = comparison_group.token_next_by(i=token_groups.Identifier)
        idx, _ = comparison_group.token_next_by(m=(token_types.Comparison, "="))
        _, column_value = comparison_group.token_next(idx, skip_ws=True, skip_cm=True)
        _, value_literal = comparison_group.token_next_by(t=token_types.Literal)
        if value_literal is None:
            raise exceptions.NotSupportedError(
                "Only updating to literal values is currently supported "
                "(e.g. can't assign one column's value to another column "
                "in a single UPDATE query)"
            )

        column_value = extract_value(value_literal)

        column = cls.from_identifier(column_identifier)
        column.value = column_value

        return column

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

    SUPPORTED_COMPARISON_OPERATORS = ["=", GREATER_THAN, ">=", "<", "<=", "IS"]

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

            next_comparison_idx, _ = where_group.token_next_by(
                m=(token_types.Keyword, "AND"), idx=idx
            )

            # I'm not sure what the exact cause is, but sometimes sqlparse has trouble
            # with grouping tokens into Comparison groups (seems to mostly be an issue
            # after the AND keyword, but not always).
            if isinstance(comparison, token_groups.Identifier):
                comparison = token_groups.Comparison(
                    where_group.tokens[idx:next_comparison_idx]
                )

            where_filter = cls._parse_comparison(comparison)
            where_filters.append(where_filter)

            idx, _ = where_group.token_next_by(m=(token_types.Keyword, "AND"), idx=idx)
            if idx is None:
                break

        return where_filters

    @classmethod
    def _parse_comparison(cls, comparison_group: token_groups.Comparison) -> Filter:
        id_idx, comparison_identifier = comparison_group.token_next_by(
            i=token_groups.Identifier
        )
        columns = Column.from_identifier_group(comparison_identifier)
        assert len(columns) == 1
        column = columns[0]

        _, comparison_operator = comparison_group.token_next_by(
            t=token_types.Comparison, m=(token_types.Keyword, "IS")
        )

        if comparison_operator.value not in cls.SUPPORTED_COMPARISON_OPERATORS:
            raise exceptions.NotSupportedError(
                "Only the following comparisons are supported in WHERE clauses: "
                ", ".join(cls.SUPPORTED_COMPARISON_OPERATORS)
            )

        value_idx, comparison_value_literal = comparison_group.token_next_by(
            t=token_types.Literal,
            m=[
                (token_types.Keyword, "NULL"),
                (token_types.Keyword, "TRUE"),
                (token_types.Keyword, "FALSE"),
            ],
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
        if operator_value == "IS":
            return "="

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
        return functools.reduce(collect_alias_maps, self.columns, {})

    def __str__(self) -> str:
        return self.name


class OrderBy:
    """Representation of result ordering in an SQL query.

    Params:
    -------
    columns: List of columns whose values determing the ordering of the results.
    direction: Direction in which the results are ordered, either 'ASC' (the default)
        or 'DESC'.
    """

    def __init__(
        self,
        columns: typing.List[Column],
        direction: OrderDirection = OrderDirection.ASC,
    ):
        assert any(columns)
        self._columns = columns
        self._direction = direction or OrderDirection.ASC

    @classmethod
    def from_statement(
        cls, statement: token_groups.Statement
    ) -> typing.Optional[OrderBy]:
        """Extract results ordering from an SQL statement.

        Params:
        -------
        statement: A full SQL statement

        Returns:
        --------
        An OrderBy object with the SQL ORDER BY attributes.
        """
        idx, order_by = statement.token_next_by(m=(token_types.Keyword, "ORDER BY"))
        if order_by is None:
            return None

        idx, identifier = statement.token_next(skip_cm=True, skip_ws=True, idx=idx)
        direction = cls._extract_direction(identifier)

        if direction is None:
            columns = Column.from_identifier_group(identifier)
        else:
            # Because of how sqlparse erroneously groups the final column identifier
            # with the direction keyword, we have to parse identifiers separately,
            # drilling down an extra level for the final token.
            nested_columns = [
                Column.from_identifier_group(token)
                for token in identifier.tokens[:-1]
                if isinstance(
                    token, (token_groups.Identifier, token_groups.IdentifierList)
                )
            ]

            # If we order by a single column, the final token will be the
            # direction keyword token. Otherwise, it will be an identifier with both
            # the final column identifier and the direction keyword.
            maybe_column_identifier = identifier.tokens[-1]
            if maybe_column_identifier.is_group:
                column_identifier = maybe_column_identifier
                _, final_column_identifier = column_identifier.token_next_by(
                    i=token_groups.Identifier
                )
                nested_columns.append(
                    Column.from_identifier_group(final_column_identifier)
                )

            columns = list(itertools.chain.from_iterable(nested_columns))

        return cls(columns=columns, direction=direction)

    @classmethod
    def _extract_direction(cls, identifier: token_groups.Identifier) -> OrderDirection:
        _, direction_token = identifier.token_next_by(t=token_types.Keyword)

        if direction_token is None:
            PENULTIMATE_TOKEN = -2
            # For some reason, when ordering by multiple columns with a direction keyword,
            # sqlparse groups the final column with the direction in an Identifier token.
            # There is an open issue (https://github.com/andialbrecht/sqlparse/issues/606),
            # though without any response, so it seems to be a bug.
            _, direction_identifier = identifier.token_next_by(
                i=token_groups.Identifier, idx=PENULTIMATE_TOKEN
            )
            if direction_identifier is not None:
                _, direction_token = direction_identifier.token_next_by(
                    t=token_types.Keyword
                )

        return (
            getattr(OrderDirection, direction_token.value) if direction_token else None
        )

    @property
    def columns(self) -> typing.List[Column]:
        """List of columns referenced in the SQL query in the order that they appear."""
        return self._columns

    @property
    def direction(self) -> OrderDirection:
        """Direction of the ordering."""
        return self._direction


class SQLQuery:
    """Representation of an entire SQL query statement.

    Params:
    -------
    tables: List of tables referenced in the query.
    columns: List of columns referenced in the query.
    distinct: Whether the results should be unique.
    order_by: Object representing how the results should be ordered.
    """

    def __init__(
        self,
        tables: typing.List[Table] = None,
        columns: typing.List[Column] = None,
        distinct: bool = False,
        order_by: typing.Optional[OrderBy] = None,
        limit: typing.Optional[int] = None,
    ):
        self.distinct = distinct
        tables = tables or []
        self._tables = tables
        columns = columns or []
        self._columns = columns
        self._order_by = order_by
        self.limit = limit

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

        idx, _ = statement.token_next_by(m=(token_types.Keyword, "LIMIT"))
        _, limit = statement.token_next(skip_cm=True, skip_ws=True, idx=idx)
        limit_value = None if limit is None else int(limit.value)

        order_by = OrderBy.from_statement(statement)

        return cls(
            tables=tables,
            columns=columns,
            distinct=bool(distinct),
            order_by=order_by,
            limit=limit_value,
        )

    @classmethod
    def _build_update_query(
        cls, statement: token_groups.Statement, table: Table
    ) -> SQLQuery:
        idx, _ = statement.token_next_by(m=(token_types.Keyword, "SET"))
        # If multiple columns are being updated, the assignment comparisons are grouped
        # in an IdentifierList. Otherwise, the Comparison token is at the top level of
        # the statement.
        _, maybe_comparison_container = statement.token_next_by(
            i=token_groups.IdentifierList, idx=idx
        )
        comparison_container = maybe_comparison_container or statement

        idx = -1
        while True:
            idx, comparison = comparison_container.token_next_by(
                i=token_groups.Comparison, idx=idx
            )
            if comparison is None:
                break

            column = Column.from_comparison_group(comparison)
            table.add_column(column)

        return cls(tables=[table], columns=table.columns)

    @classmethod
    def _build_insert_query(
        cls, statement: token_groups.Statement, table: Table
    ) -> SQLQuery:
        _, function_group = statement.token_next_by(i=token_groups.Function)

        if function_group is None:
            raise exceptions.NotSupportedError(
                "INSERT INTO statements without column names are not currently supported."
            )

        _, column_name_group = function_group.token_next_by(i=token_groups.Parenthesis)
        _, column_name_identifiers = column_name_group.token_next_by(
            i=(token_groups.IdentifierList, token_groups.Identifier)
        )

        _, value_group = statement.token_next_by(i=token_groups.Values)
        val_idx, column_value_group = value_group.token_next_by(
            i=token_groups.Parenthesis
        )

        _, additional_parenthesis_group = value_group.token_next_by(
            i=token_groups.Parenthesis, idx=val_idx
        )
        if additional_parenthesis_group is not None:
            raise exceptions.NotSupportedError(
                "INSERT for multiple rows is not supported yet."
            )

        _, column_value_identifiers = column_value_group.token_next_by(
            i=(token_groups.IdentifierList, token_groups.Identifier),
        )
        # If there's just one value in the VALUES clause, it doesn't get wrapped in an Identifer
        column_value_identifiers = column_value_identifiers or column_value_group

        idx = -1

        for column in Column.from_identifier_group(column_name_identifiers):
            idx, column_value = column_value_identifiers.token_next_by(
                t=[token_types.Literal, token_types.Keyword], idx=idx
            )

            if column_value is None:
                raise exceptions.NotSupportedError(
                    "Assigning values dynamically is not supported. "
                    "You must use literal values only in INSERT statements."
                )

            column.value = extract_value(column_value)
            table.add_column(column)

        return cls(tables=[table], columns=table.columns)

    @classmethod
    def _build_delete_query(cls, table: Table) -> SQLQuery:
        return cls(tables=[table])

    @property
    def tables(self) -> typing.List[Table]:
        """List of data tables referenced in the SQL query."""
        return self._tables

    @property
    def columns(self) -> typing.List[Column]:
        """List of columns referenced in the SQL query in the order that they appear."""
        return self._columns

    @property
    def order_by(self) -> typing.Optional[OrderBy]:
        """How the results of the query should be ordered."""
        return self._order_by

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
