"""Collection of objects representing RDB structures in SQL queries"""

from __future__ import annotations
import functools
import itertools
import typing
import enum


from sqlparse import sql as token_groups, tokens as token_types

from sqlalchemy_fauna import exceptions
from . import sql_table, common


class OrderDirection(enum.Enum):
    """Enum for direction of results ordering."""

    ASC = "ASC"
    DESC = "DESC"


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
        columns: typing.List[sql_table.Column],
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
            columns = sql_table.Column.from_identifier_group(identifier)
        else:
            # Because of how sqlparse erroneously groups the final column identifier
            # with the direction keyword, we have to parse identifiers separately,
            # drilling down an extra level for the final token.
            nested_columns = [
                sql_table.Column.from_identifier_group(token)
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
                    sql_table.Column.from_identifier_group(final_column_identifier)
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
    def columns(self) -> typing.List[sql_table.Column]:
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
        tables: typing.List[sql_table.Table] = None,
        distinct: bool = False,
        order_by: typing.Optional[OrderBy] = None,
        limit: typing.Optional[int] = None,
    ):
        self.distinct = distinct
        tables = tables or []
        self._tables = tables
        self._order_by = order_by
        self.limit = limit

        assert len({col.position for col in self.columns}) == len(self.columns), (
            "All columns in an SQLQuery must have unique position values to avoid "
            "ambiguity"
        )

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
        for where_filter in sql_table.Filter.from_where_group(where_group):
            sql_instance.add_filter_to_table(where_filter)

        return sql_instance

    @classmethod
    def _collect_tables(
        cls, statement: token_groups.Statement
    ) -> typing.List[sql_table.Table]:
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
        tables = [sql_table.Table.from_identifier(table_identifier)]

        while True:
            idx, join_kw = statement.token_next_by(
                m=(token_types.Keyword, "JOIN"), idx=idx
            )
            if join_kw is None:
                break

            idx, table_identifier = statement.token_next(
                idx, skip_ws=True, skip_cm=True
            )
            table = sql_table.Table.from_identifier(table_identifier)

            idx, comparison_group = statement.token_next_by(
                i=token_groups.Comparison, idx=idx
            )

            table.add_join(tables[-1], comparison_group, sql_table.JoinDirection.LEFT)
            tables.append(table)

        return tables

    @classmethod
    def _build_select_query(
        cls, statement: token_groups.Statement, tables: typing.List[sql_table.Table]
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

        for column in sql_table.Column.from_identifier_group(identifiers):
            try:
                table = next(
                    table for table in tables if table.name == column.table_name
                )
            except StopIteration:
                table = tables[0]

            table.add_column(column)

        _, distinct = statement.token_next_by(m=(token_types.Keyword, "DISTINCT"))

        idx, _ = statement.token_next_by(m=(token_types.Keyword, "LIMIT"))
        _, limit = statement.token_next(skip_cm=True, skip_ws=True, idx=idx)
        limit_value = None if limit is None else int(limit.value)

        order_by = OrderBy.from_statement(statement)

        return cls(
            tables=tables,
            distinct=bool(distinct),
            order_by=order_by,
            limit=limit_value,
        )

    @classmethod
    def _build_update_query(
        cls, statement: token_groups.Statement, table: sql_table.Table
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
        position = 0
        while True:
            idx, comparison = comparison_container.token_next_by(
                i=token_groups.Comparison, idx=idx
            )
            if comparison is None:
                break

            column = sql_table.Column.from_comparison_group(comparison, position)
            table.add_column(column)
            position = position + 1

        return cls(tables=[table])

    @classmethod
    def _build_insert_query(
        cls, statement: token_groups.Statement, table: sql_table.Table
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

        for column in sql_table.Column.from_identifier_group(column_name_identifiers):
            idx, column_value = column_value_identifiers.token_next_by(
                t=[token_types.Literal, token_types.Keyword], idx=idx
            )

            if column_value is None:
                raise exceptions.NotSupportedError(
                    "Assigning values dynamically is not supported. "
                    "You must use literal values only in INSERT statements."
                )

            column.value = common.extract_value(column_value)
            table.add_column(column)

        return cls(tables=[table])

    @classmethod
    def _build_delete_query(cls, table: sql_table.Table) -> SQLQuery:
        return cls(tables=[table])

    @property
    def tables(self) -> typing.List[sql_table.Table]:
        """List of data tables referenced in the SQL query."""
        return self._tables

    @property
    def columns(self) -> typing.List[sql_table.Column]:
        """List of columns referenced in the SQL query in the order that they appear."""
        column_list: typing.List[sql_table.Column] = []
        return sorted(
            functools.reduce(
                lambda acc, table: list(acc) + table.columns, self.tables, column_list
            ),
            key=lambda column: column.position,
        )

    @property
    def order_by(self) -> typing.Optional[OrderBy]:
        """How the results of the query should be ordered."""
        return self._order_by

    @property
    def has_functions(self) -> bool:
        """"Whether the SQL query has any functions in its selected columns."""
        return any(col.is_function for col in self.columns)

    @property
    def alias_map(self) -> sql_table.TableAliasMap:
        """Nested dictionaries for all columna/alias mapping in the SQL query."""
        collect_alias_maps = lambda acc, table: {**acc, **table.alias_map}
        return functools.reduce(collect_alias_maps, self.tables, {})

    def add_filter_to_table(self, sql_filter: sql_table.Filter):
        """Associates the given Filter with the Table that it applies to.

        Params:
        -------
        sql_filter: An instance of table.Filter.
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
