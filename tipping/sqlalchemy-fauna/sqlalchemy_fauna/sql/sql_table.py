"""Classes that represent relational data tables and their columns in SQL."""

from __future__ import annotations

import functools
import typing
from datetime import datetime
import re
import enum

from sqlparse import sql as token_groups, tokens as token_types
from mypy_extensions import TypedDict

from sqlalchemy_fauna import exceptions
from . import common


ColumnAliasMap = typing.Dict[str, str]
TableAliasMap = typing.Dict[typing.Optional[str], ColumnAliasMap]


class Function(enum.Enum):
    """Enum for identifying SQL functions."""

    COUNT = "COUNT"


class JoinDirection(enum.Enum):
    """Enum for table join directions."""

    LEFT = "left"
    RIGHT = "right"


class SetOperation(enum.Enum):
    """Enum for types of operations for joining sets."""

    INTERSECTION = "intersection"
    UNION = "union"


ColumnParams = TypedDict(
    "ColumnParams",
    {
        "table_name": typing.Optional[str],
        "name": str,
        "alias": str,
        "function_name": typing.Optional[Function],
        "position": int,
    },
)


# Probably not a complete list, but covers the basics
FUNCTION_NAMES = {"min", "max", "count", "avg", "sum"}
GREATER_THAN = ">"
LESS_THAN = "<"

NOT_SUPPORTED_FUNCTION_REGEX = re.compile(r"^(?:MIN|MAX|AVG|SUM)\(.+\)$", re.IGNORECASE)
COUNT_REGEX = re.compile(r"^COUNT\(.+\)$", re.IGNORECASE)

REVERSE_JOIN = {
    JoinDirection.LEFT: JoinDirection.RIGHT,
    JoinDirection.RIGHT: JoinDirection.LEFT,
}


class Column:
    """Representation of a column object in SQL.

    Params:
    identifier: Parsed SQL Identifier for a column name and/or alias.
    """

    def __init__(
        self,
        name: str,
        alias: str,
        position: int,
        table_name: typing.Optional[str] = None,
        value: typing.Optional[typing.Union[str, int, float, datetime]] = None,
        function_name: typing.Optional[Function] = None,
    ):
        self.name = name
        self.alias = alias
        self.position = position
        self.value = value
        self._function_name = function_name
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
            columns = []
            idx = 0

            for identifier in identifiers:
                if not isinstance(identifier, token_groups.Identifier):
                    continue

                columns.append(Column.from_identifier(identifier, idx))
                idx = idx + 1

            return columns

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
    def from_identifier(
        cls, identifier: token_groups.Identifier, position: int = 0
    ) -> Column:
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
            "position": position,
        }

        return Column(**column_params)

    @classmethod
    def from_comparison_group(
        cls, comparison_group: token_groups.Comparison, position: int = 0
    ) -> Column:
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

        column_value = common.extract_value(value_literal)

        column = cls.from_identifier(column_identifier, position)
        column.value = column_value

        return column

    @property
    def table(self) -> typing.Optional[Table]:
        """Table object associated with this column."""
        return self._table

    @table.setter
    def table(self, table: Table):
        assert self.table_name is None or self.belongs_to_table(table)

        self._table = table
        self._table_name = table.name

    @property
    def table_name(self) -> typing.Optional[str]:
        """Name of the associated table in the SQL query."""
        return self._table_name

    def belongs_to_table(self, table: Table) -> bool:
        """Whether this column is associated with the given table."""
        return self.table_name in (table.name, table.alias)

    @property
    def alias_map(self) -> ColumnAliasMap:
        """Dictionary that maps the column name to its alias in the SQL query."""
        return {self.name: self.alias}

    @property
    def function_name(self) -> typing.Optional[str]:
        """Name of a function to be applied to the query results."""
        return None if self._function_name is None else self._function_name.value

    @property
    def is_function(self) -> bool:
        """Whether the column represents the result of an SQL function."""
        return self._function_name is not None

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
    def from_comparison_group(cls, comparison_group: token_groups.Comparison) -> Filter:
        """Parse a Comparison group to build a Filter object.

        Params:
        -------
        comparison_group: A Comparison token generated by sqlparse.

        Returns:
        --------
        An instance of Filter.
        """
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
        comparison_value = common.extract_value(comparison_value_literal)
        operator_value = cls._extract_operator_value(
            comparison_operator.value, id_idx, value_idx
        )

        return cls(
            column=column,
            operator=operator_value,
            value=comparison_value,
        )

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

    def belongs_to_table(self, table: Table) -> bool:
        """Whether this column is associated with the given table."""
        return self.table_name in (table.name, table.alias)

    @property
    def table(self) -> typing.Optional[Table]:
        """Table object associated with this column."""
        return self._table

    @table.setter
    def table(self, table: Table):
        assert self.table_name is None or self.belongs_to_table(table)

        self._table = table
        self._table_name = table.name

    @property
    def table_name(self) -> typing.Optional[str]:
        """Name of the associated table in the SQL query."""
        return self._table_name

    @property
    def name(self) -> str:
        """Unique name of the filter based on its query parameters."""
        return f"{self.table_name}_{self.column.name}_{self.operator}_{self.value}"


class FilterGroup:
    """Representation of a group of WHERE clauses all separated by ANDs or ORs.

    Each instance represents an intersection (all ANDs) or union (all ORs) of clauses.

    Params:
    -------
    filters: List of SQL comparisons used for filtering results (e.g. <column> = <value>).
    """

    def __init__(
        self,
        set_operation: SetOperation,
        filters: typing.List[Filter] = None,
        filter_groups: typing.List[FilterGroup] = None,
    ):
        self.set_operation = set_operation
        self._filters = filters or typing.cast(typing.List[Filter], [])
        self._filter_groups = filter_groups or typing.cast(typing.List[FilterGroup], [])

    @classmethod
    def from_where_group(
        cls, where_group: typing.Optional[token_groups.Where], idx=-1
    ) -> FilterGroup:
        """Parse a WHERE token to extract all filter groups contained therein.

        Params:
        -------
        where_group: A Where SQL token from sqlparse.

        Returns:
        --------
        A FilterGroup instances based on all conditions contained within the WHERE clause.
        """
        if where_group is None:
            return cls(set_operation=SetOperation.INTERSECTION)

        _, between_keyword = where_group.token_next_by(
            m=(token_types.Keyword, "BETWEEN")
        )
        if between_keyword is not None:
            raise exceptions.NotSupportedError(
                "BETWEEN not yet supported in WHERE clauses."
            )

        _, parenthesis_group = where_group.token_next_by(i=token_groups.Parenthesis)
        if parenthesis_group is not None:
            raise exceptions.NotSupportedError(
                "Nested WHERE conditions are not supported."
            )

        root_set_operation = SetOperation.INTERSECTION
        token_chunks: typing.List[typing.List[token_types.Token]] = []
        tokens: typing.List[token_types.Token] = []
        idx = -1

        while True:
            idx, token = where_group.token_next_by(
                m=(token_types.Keyword, "OR"),
                i=(token_groups.Comparison, token_groups.Identifier),
                idx=idx,
            )
            if token is None:
                token_chunks.append(tokens)
                break

            if token.match(token_types.Keyword, "OR"):
                token_chunks.append(tokens)
                tokens = []
                root_set_operation = SetOperation.UNION
                continue

            if isinstance(token, token_groups.Comparison):
                tokens.append(token)
                continue

            if isinstance(token, token_groups.Identifier):
                (next_conjunction, _) = where_group.token_next_by(
                    m=[(token_types.Keyword, "AND"), (token_types.Keyword, "OR")],
                    idx=idx,
                )
                # I'm not sure what the exact cause is, but sometimes sqlparse has trouble
                # with grouping tokens into Comparison groups (seems to mostly be an issue
                # after the AND keyword, but not always).
                tokens.append(
                    token_groups.Comparison(where_group.tokens[idx:next_conjunction])
                )
                continue

            raise exceptions.NotSupportedError(
                f"SQL token '{str(token)}' not supported as part of a WHERE clause."
            )

        filter_groups: typing.List[FilterGroup] = []
        filters: typing.List[Filter] = []
        idx = 0

        for token_chunk in token_chunks:
            if len(token_chunks) == 1 or len(token_chunk) == 1:
                filters.extend(
                    [Filter.from_comparison_group(token) for token in token_chunk]
                )
                continue

            group_filters = [
                Filter.from_comparison_group(token)
                for token in token_chunk
                if isinstance(token, token_groups.Comparison)
            ]
            filter_groups.append(
                cls(set_operation=SetOperation.INTERSECTION, filters=group_filters)
            )

        return cls(
            set_operation=root_set_operation,
            filter_groups=filter_groups,
            filters=filters,
        )

    @property
    def filters(self) -> typing.List[Filter]:
        """List of filters contained within this group.

        Doesn't include filters contained in nested filter groups.
        """
        return self._filters

    @property
    def filter_groups(self) -> typing.List[FilterGroup]:
        """List of filter groups contained within this group.

        Doesn't include filter groups contained in nested filter groups.
        """
        return self._filter_groups


class Table:
    """Representation of a table object in SQL.

    Params:
    -------
    name: Name of the table.
    alias: Alias of the table.
    columns: Column objects that belong to the given table.
    filters: Filter objects that are applied to the table's query results.
    """

    def __init__(
        self,
        name: str,
        alias: typing.Optional[str] = None,
        columns: typing.Optional[typing.List[Column]] = None,
        filters: typing.Optional[typing.List[Filter]] = None,
    ):
        self.name = name
        self.alias = alias
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
        idx, name = identifier.token_next_by(t=token_types.Name)
        assert name is not None

        idx, _ = identifier.token_next_by(m=(token_types.Keyword, "AS"), idx=idx)
        if idx is None:
            return cls(name=name.value)

        _, alias = identifier.token_next_by(i=token_groups.Identifier, idx=idx)
        if alias is None:
            return cls(name=name.value)

        return cls(name=name.value, alias=alias.value)

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
            if join_column.belongs_to_table(self)
        )
        setattr(self, f"{direction.value}_join_key", join_key)

        foreign_join_key = next(
            join_column
            for join_column in join_columns
            if join_column.belongs_to_table(foreign_table)
        )
        setattr(
            foreign_table,
            f"{REVERSE_JOIN[direction].value}_join_key",
            foreign_join_key,
        )

    @property
    def alias_map(self) -> TableAliasMap:
        """Dictionary that maps column names to their aliases in the SQL query."""
        collect_alias_maps = lambda acc, col: {
            **acc,
            col.table_name: {**acc.get(col.table_name, {}), **col.alias_map},
        }
        return functools.reduce(collect_alias_maps, self.columns, {})

    @property
    def has_columns(self) -> bool:
        """Whether this table has columns selected or modified by the query."""
        return any(self.columns)

    def __str__(self) -> str:
        return self.name
