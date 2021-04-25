# pylint: disable=missing-docstring

"""Default error classes for SQLAlchemy Dialects."""


class Error(Exception):
    pass


class Warning(Exception):  # pylint: disable=redefined-builtin
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class DataError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass
