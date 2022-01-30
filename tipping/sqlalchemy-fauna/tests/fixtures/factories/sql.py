"""Factories for SQLQuery objects."""

from __future__ import annotations
from datetime import timezone, datetime
import typing

import factory
from faker import Faker
import numpy as np

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
    table_name = factory.Faker("word")
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

    name = factory.Faker("word")
    alias = factory.Faker("word")

    @factory.post_generation
    def columns(  # pylint: disable=no-self-argument,missing-function-docstring
        table, _create, columns_param, **kwargs
    ):
        columns_to_add = (
            [
                ColumnFactory(table_name=table.name, **kwargs)
                for _ in range(np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE))
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
        filters_to_add = (
            [
                FilterFactory(column__table_name=table.name, **kwargs)
                for _ in range(np.random.randint(*ARBITRARY_SUBFACTORY_COUNT_RANGE))
            ]
            if filters_param is None
            else filters_param
        )

        for sql_filter in filters_to_add:
            table.add_filter(sql_filter)
