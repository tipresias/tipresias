"""Factories for SQLQuery objects."""

from __future__ import annotations
from datetime import timezone, datetime
from random import shuffle
import typing
from copy import deepcopy

import factory
from faker import Faker
import numpy as np
import sqlparse

from sqlalchemy_fauna import sql


Fake = Faker()


# Arbitrary filter count range to keep the list reasonably small
ARBITRARY_SUBFACTORY_COUNT_RANGE = (1, 6)


def _define_value(data_type: type):
    if data_type is None:
        return None

    if data_type == str:
        return Fake.company()

    if data_type == int:
        return Fake.pyint()

    if data_type == float:
        return Fake.pyfloat()

    if data_type == datetime:
        return Fake.date_time(tzinfo=timezone.utc)

    raise Exception(f"Unknown type, {data_type}, for column value.")


class ColumnFactory(factory.Factory):
    """Factory class for SQL Column objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.Column
        strategy = factory.BUILD_STRATEGY

    class Params:
        """
        Params for modifying the factory's default attributes.

        Params:
        -------
        data_type: A factory param that defines the data type of the column value. Possible
            values are 'str', 'int', 'float', 'datetime', 'None'. The default value is
            'str'.
        """

        data_type: typing.Optional[type] = str

    name = factory.Faker("first_name")
    alias = factory.Faker("first_name")
    position = factory.Faker("pyint")
    table_name = factory.Faker("first_name")
    function_name = None

    @factory.lazy_attribute
    def value(self):
        """Generate a random value based on the column's data_type param."""
        return _define_value(self.data_type)


class ComparisonFactory(factory.Factory):
    """Factory class for SQL Comparison objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.Comparison
        strategy = factory.BUILD_STRATEGY

    operator = np.random.choice(list(sql.Comparison.OPERATOR_MAP.values()))  # type: ignore


class FilterFactory(factory.Factory):
    """Factory class for SQL Filter objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.Filter
        strategy = factory.BUILD_STRATEGY

    column = factory.SubFactory(ColumnFactory)
    comparison = factory.SubFactory(ComparisonFactory)

    @factory.lazy_attribute
    def value(self):
        """Generate a random value based on the associated column's data_type param."""
        data_type = None if self.column.value is None else type(self.column.value)
        return _define_value(data_type)


class FilterGroupFactory(factory.Factory):
    """Factory class for SQL FilterGroup objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.FilterGroup
        strategy = factory.BUILD_STRATEGY

    filters = factory.RelatedFactoryList(
        FilterFactory, size=lambda: np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE)
    )


class TableFactory(factory.Factory):
    """Factory class for SQL Table objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.Table
        strategy = factory.BUILD_STRATEGY

    name = factory.Faker("first_name")
    alias = factory.Faker("first_name")

    @factory.post_generation
    def columns(  # pylint: disable=no-self-argument,missing-function-docstring
        table, _create, columns_param, **kwargs
    ):
        column_count = kwargs.pop(
            "count", np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE)
        )
        columns_to_add = (
            [
                ColumnFactory(table_name=table.name, **kwargs)
                for _ in range(column_count)
            ]
            if columns_param is None
            else columns_param
        )

        for column in columns_to_add:
            table.add_column(column)

    @factory.post_generation
    def filters(  # pylint: disable=no-self-argument,missing-function-docstring
        table, _create, filters_param, **kwargs
    ):
        filter_count = kwargs.pop(
            "count", np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE)
        )
        filters_to_add = (
            [
                FilterFactory(column__table_name=table.name, **kwargs)
                for _ in range(filter_count)
            ]
            if filters_param is None
            else filters_param
        )

        for sql_filter in filters_to_add:
            table.add_filter(sql_filter)


class OrderByFactory(factory.Factory):
    """Factory class for OrderBy objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.OrderBy
        strategy = factory.BUILD_STRATEGY

    direction = factory.LazyAttribute(
        lambda _: (np.random.choice(list(sql.sql_query.OrderDirection)))  # type: ignore
    )

    # Have to make this a LazyAttribute rather than RelatedFactory,
    # because OrderBy requires a populated columns param on instantiation,
    # and RelatedFactory creates objects post-instantiation.
    @factory.lazy_attribute
    def columns(self):  # pylint: disable=missing-function-docstring,no-self-use
        # We don't currently support ordering by more than one column per query
        return [ColumnFactory()]


class SQLQueryFactory(factory.Factory):
    """Factory class for SQLQuery objects."""

    class Meta:
        """Factory attributes for recreating the associated model's attributes."""

        model = sql.SQLQuery
        strategy = factory.BUILD_STRATEGY

    class Params:
        """
        Params for modifying the factory's default attributes.

        Params:
        -------
        table_count: Number of tables to include in the SQLQuery. Defaults to a random number
            from 1 to 5 (inclusive).
        """

        table_count = None

    query_string = "NOT A REAL SQL STRING"
    distinct = False
    limit = None

    @factory.lazy_attribute
    def tables(self):  # pylint: disable=missing-function-docstring,no-self-use
        table_count = (
            np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE)
            if self.table_count is None
            else self.table_count
        )
        table_with_columns = np.random.randint(0, table_count)
        tables_to_add = [
            # We make filters empty in order to add them via FilterGroups
            # associated with the SQLQuery
            TableFactory(columns=(None if n == table_with_columns else []), filters=[])
            for n in range(table_count)
        ]

        for idx, table in enumerate(tables_to_add):
            if idx == 0:
                continue

            last_table_name = tables_to_add[idx - 1].name
            table_names = [last_table_name, table.name]
            shuffle(table_names)
            parent_table, child_table = table_names
            # Using .parse() to generate the Comparison token group object,
            # because building it manually from sub-tokens is more trouble.
            statement = sqlparse.parse(
                f"{parent_table}.id = {child_table}.{parent_table}_id"
            )[0]
            comparison = statement.tokens[0]

            table.add_join(
                tables_to_add[idx - 1],
                comparison,
                sql.sql_table.JoinDirection.LEFT,
            )

        return tables_to_add

    @factory.post_generation
    def filter_groups(  # pylint: disable=no-self-argument,missing-function-docstring
        sql_query, _create, filter_groups_param, **kwargs
    ):
        filter_group_kwargs = deepcopy(kwargs)

        build_filters = lambda: [
            # We generate the filters individually to avoid giving them
            # random table names that have nothing to do with this SQLQuery
            # or assigning all filters from a given FilterGroup
            # to the same table via factory params.
            FilterFactory(column__table_name=np.random.choice(sql_query.tables))
            for _ in range(np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE))
        ]

        filter_groups_to_add = (
            [
                FilterGroupFactory(
                    filters=build_filters(),
                    **filter_group_kwargs,
                )
            ]
            if filter_groups_param is None
            else filter_groups_param
        )

        for filter_group in filter_groups_to_add:
            sql_query.add_filter_group(filter_group)

    @factory.post_generation
    def order_by(  # pylint: disable=no-self-argument,missing-function-docstring
        sql_query, _create, order_by_param, **kwargs
    ):
        if order_by_param is not None:
            sql_query._order_by = (  # pylint: disable=attribute-defined-outside-init
                order_by_param
            )
            return None

        query_columns = deepcopy(sql_query.columns)
        shuffle(query_columns)

        # We currently only support ordering by one column at a time, so no reason to create
        # invalid attributes by default.
        order_by_col_count = np.random.randint(0, 2)
        order_by_columns = query_columns[:order_by_col_count]

        if len(order_by_columns) > 0:
            sql_query._order_by = (  # pylint: disable=attribute-defined-outside-init
                OrderByFactory(columns=order_by_columns, **kwargs)
            )

        return None
