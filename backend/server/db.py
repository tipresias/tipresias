"""Module for connecting models with the database."""

from __future__ import annotations
from typing import Tuple, Dict

from django.db import models


class DBRecordCollection:
    """Collection of team records that can trigger further DB queries."""

    def __init__(self, records_collection: models.QuerySet):
        self.records_collection = records_collection

    def __len__(self):
        return len(self.records_collection)

    def __iter__(self):
        return (team for team in self.records_collection)

    def delete(self) -> Tuple[int, Dict[str, int]]:
        """Delete all team match records in the collection."""
        return self.records_collection.delete()

    def count(self) -> int:
        """
        Get the number of team match records in the collection.

        Returns:
        --------
        Count of team match records.
        """
        return self.records_collection.count()

    def order_by(self, ordering_attribute: str) -> DBRecordCollection:
        """
        Order the collection elements by the given attribute(s).

        Params:
        -------
        ordering_attribute: Name of the attribute. Optionally prepend '-'
            to sort in descending order.

        Returns:
        --------
        Sorted team match collection.
        """
        return self.records_collection.order_by(ordering_attribute)

    def update(self, **attributes) -> DBRecordCollection:
        """
        Update all TeamMatch records in the collection with the given attribute values.

        Params:
        -------
        attributes: TeamMatch attribute values to update.

        Returns:
        --------
        Count of updated records.
        """
        return self.records_collection.update(**attributes)


class DBQuery(models.Model):
    """Interface for performing database queries."""

    @classmethod
    def create(cls, **attributes) -> models.Model:
        """
        Create a TeamMatch record in the database.

        Params:
        -------
        attributes: TeamMatch attributes for the created record.

        Returns:
        --------
        An instance of the created team match.
        """
        return cls.objects.create(**attributes)

    @classmethod
    def count(cls) -> int:
        """
        Get the number of TeamMatch records in the database.

        Returns:
        --------
        Count of team match records.
        """
        return cls.objects.count()

    @classmethod
    def get(cls, **attributes) -> models.Model:
        """
        Get a TeamMatch record that matches the given attributes from the database.

        Params:
        -------
        attributes: TeamMatch attributes for the created record.

        Returns:
        --------
        The requested team match record.
        """
        return cls.objects.get(**attributes)

    @classmethod
    def get_or_create(cls, **attributes) -> Tuple[models.Model, bool]:
        """
        Get a TeamMatch record that matches the given attributes or create it if missing.

        Params:
        -------
        attributes: TeamMatch attributes for the requested/created record.

        Returns:
        --------
        The requested team match record and whether it was created.
        """
        return cls.objects.get_or_create(**attributes)

    @classmethod
    def all(cls) -> DBRecordCollection:
        """
        Get all TeamMatch records from the database.

        Returns:
        --------
        A list of team match records.
        """
        return DBRecordCollection(cls.objects.all())

    @classmethod
    def filter(cls, **attributes) -> DBRecordCollection:
        """
        Get all TeamMatch records that match the given filter values.

        Params:
        -------
        attributes: TeamMatch attributes to filter by.

        Returns:
        --------
        A list of team match records.
        """
        return DBRecordCollection(cls.objects.filter(**attributes))