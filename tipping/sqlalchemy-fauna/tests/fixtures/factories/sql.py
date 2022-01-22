"""Factories for SQLQuery objects."""

from __future__ import annotations
import enum
from datetime import timezone

import factory
from faker import Faker

from sqlalchemy_fauna import sql


Fake = Faker()


class DataType(enum.Enum):
    """Available data types for a column value."""

    NONE = "None"
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    DATETIME = "datetime"


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

        data_type: DataType = DataType.STRING

    name = factory.Faker("first_name")
    alias = factory.Faker("first_name")
    position = factory.Faker("pyint")
    table_name = factory.Faker("word")
    function_name = None

    @factory.lazy_attribute
    def value(self):
        """Generate a random value based on the column's data_type param."""
        if self.data_type == DataType.NONE:
            return None

        if self.data_type == DataType.STRING:
            return Fake.company()

        if self.data_type == DataType.INTEGER:
            return Fake.pyint()

        if self.data_type == DataType.FLOAT:
            return Fake.pyfloat()

        if self.data_type == DataType.DATETIME:
            return Fake.date_time(tzinfo=timezone.utc)

        raise Exception(f"Unknown DataType, {self.data_type}, for column value.")
