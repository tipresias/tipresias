"""DBAPI for use in the FaunaDialect."""

from functools import reduce
from typing import Dict, Any, List, Tuple, Union, Optional, Sequence, cast
from datetime import date, datetime, time

from faunadb.client import FaunaClient
import sqlparse
from sqlparse import tokens as token_types
from sqlparse import sql as token_groups

from . import exceptions
from .fauna import FaunaClient, translation


PopulatedResultDescription = Tuple[Optional[str], Any, None, None, None, None, bool]
ResultDescription = List[Union[Tuple, PopulatedResultDescription]]
ResultData = List[Sequence]


def connect(**connect_kwargs):
    """Create a connection with Fauna."""
    return FaunaConnection(**connect_kwargs)


def check_closed(f):
    """Decorator that checks if connection/cursor is closed.

    Copied from other examples of 3rd-party Dialects.
    """

    def g(self, *args, **kwargs):
        if self.closed:
            raise exceptions.Error(
                "{klass} already closed".format(klass=self.__class__.__name__)
            )
        return f(self, *args, **kwargs)

    return g


def check_result(f):
    """Decorator that checks if the cursor has results from `execute`.

    Copied from other examples of 3rd-party Dialects.
    """

    def g(self, *args, **kwargs):
        if self._results is None:  # pylint: disable=protected-access
            raise exceptions.Error("Called before `execute`")
        return f(self, *args, **kwargs)

    return g


class FaunaQuery:
    """Query object for Fauna."""

    def __init__(self, client: FaunaClient):
        self.client = client

    def execute(self, query: str) -> Tuple[ResultData, ResultDescription]:
        """Execute an SQL query as a Fauna query."""
        result = self.client.sql(query)

        data: ResultData = [tuple(document.values()) for document in result]
        description: ResultDescription = self._get_description_from_data(
            result
        ) or self._get_description_from_query(query)

        return data, description

    def _get_description_from_data(
        self, result: List[Dict[str, Any]]
    ) -> Optional[ResultDescription]:
        """
        Return description from the result of the SQL query.

        We only return the name, type (inferred from the values) and if the values
        can be NULL.
        """
        if not any(result):
            return None

        return [
            (
                key,  # name
                self._infer_field_type(value),  # type_code
                None,  # [display_size]
                None,  # [internal_size]
                None,  # [precision]
                None,  # [scale]
                True,  # [null_ok]
            )
            for key, value in result[0].items()
        ]

    def _get_description_from_query(self, query: str):
        sql_statements = sqlparse.parse(query)

        if len(sql_statements) > 1:
            raise exceptions.NotSupportedError(
                "Only one SQL statement at a time is currently supported. "
                f"The following query has more than one:\n{query}"
            )

        sql_statement = sql_statements[0]

        _, wildcard = sql_statement.token_next_by(t=token_types.Wildcard)

        if wildcard:
            return [
                (
                    None,  # name
                    None,  # type_code
                    None,  # [display_size]
                    None,  # [internal_size]
                    None,  # [precision]
                    None,  # [scale]
                    True,  # [null_ok]
                )
            ]

        _, identifiers = sql_statement.token_next_by(
            i=(
                token_groups.Identifier,
                token_groups.IdentifierList,
                token_groups.Function,
            )
        )
        table_column_alias_map = translation.parse_identifiers(identifiers)
        acc_map: Dict[str, str] = {}
        column_alias_map = reduce(
            lambda acc, curr: acc if any(acc) else curr[1],
            table_column_alias_map.items(),
            acc_map,
        )

        return [
            (
                alias_name or column_name,  # name
                None,  # type_code
                None,  # [display_size]
                None,  # [internal_size]
                None,  # [precision]
                None,  # [scale]
                True,  # [null_ok]
            )
            for column_name, alias_name in column_alias_map.items()
        ]

    def _parse_identifiers(
        self, identifiers: Union[token_groups.Identifier, token_groups.IdentifierList]
    ) -> Tuple[Sequence[Optional[str]], Sequence[str], Sequence[Optional[str]]]:
        if isinstance(identifiers, token_groups.Identifier):
            table_name, column_name, alias_name = self._parse_identifier(identifiers)
            return ((table_name,), (column_name,), (alias_name,))

        return cast(
            Tuple[Sequence[Optional[str]], Sequence[str], Sequence[Optional[str]]],
            tuple(
                zip(
                    *[
                        self._parse_identifier(identifier)
                        for identifier in identifiers
                        if isinstance(identifier, token_groups.Identifier)
                    ]
                )
            ),
        )

    @staticmethod
    def _parse_identifier(
        identifier: token_groups.Identifier,
    ) -> Tuple[Optional[str], str, Optional[str]]:
        idx, identifier_name = identifier.token_next_by(t=token_types.Name)

        tok_idx, next_token = identifier.token_next(idx, skip_ws=True)
        if next_token and next_token.match(token_types.Punctuation, "."):
            idx = tok_idx
            table_name = identifier_name.value
            idx, column_identifier = identifier.token_next_by(
                t=token_types.Name, idx=idx
            )
            column_name = column_identifier.value
        else:
            table_name = None
            column_name = identifier_name.value

        idx, as_keyword = identifier.token_next_by(
            m=(token_types.Keyword, "AS"), idx=idx
        )

        if as_keyword is not None:
            _, alias_identifier = identifier.token_next_by(
                i=token_groups.Identifier, idx=idx
            )
            alias_name = alias_identifier.value
        else:
            alias_name = None

        return (table_name, column_name, alias_name)

    @staticmethod
    def _infer_field_type(value: Any) -> Optional[str]:
        if isinstance(value, str):
            return "string"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, date):
            return "date"
        if isinstance(value, datetime):
            return "datetime"
        if isinstance(value, time):
            return "timeofday"
        # We currently have no way of inferring field type from None values,
        # so we return None per _get_description_from_query
        if value is None:
            return None

        raise Exception(f"{value} has unknown data type {type(value)}")


class FaunaConnection:
    """Connection to a Fauna DB instance."""

    def __init__(self, host="", port=None, secret="", scheme=""):
        client = FaunaClient(scheme=scheme, domain=host, port=port, secret=secret)
        self._fauna_query = FaunaQuery(client=client)
        self.closed = False
        self.cursors = []

    @check_closed
    def close(self):
        """Close the connection to the database."""
        self.closed = True
        for cursor in self.cursors:
            try:
                cursor.close()
            except exceptions.Error:
                pass  # already closed

    @check_closed
    def commit(self):
        """
        Commit any pending transaction to the database.

        Not supported.
        """

    @check_closed
    def cursor(self):
        """Return a new Cursor Object using the connection."""
        cursor = FaunaCursor(fauna_query=self._fauna_query)
        self.cursors.append(cursor)

        return cursor

    @check_closed
    def execute(self, operation, parameters=None):
        """Execute an SQL query."""
        cursor = self.cursor()
        return cursor.execute(operation, parameters)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def apply_parameters(operation, parameters):
    """Clean parameters and apply them to the DB query."""
    escaped_parameters = {key: escape(value) for key, value in parameters.items()}
    return operation % escaped_parameters


def escape(value):
    """Clean parameter values."""
    if value == "*":
        return value
    if isinstance(value, str):
        return "'{}'".format(value.replace("'", "''"))
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if not isinstance(value, str):
        # Numpy integers and floats are technically not instances of int or float,
        # so we make sure that we don't have a numeric string, then check if it's numeric
        # via brute force.
        try:
            int(value)
            return str(value)
        except TypeError:
            pass
    if isinstance(value, (datetime, date)):
        # We have to treat datetimes as strings in the SQL query, because otherwise sqlparser
        # doesn't know what to do with them
        return f"'{value.isoformat()}'"
    if isinstance(value, (list, tuple)):
        return "({0})".format(", ".join(escape(element) for element in value))


class FaunaCursor:
    """Fauna connection cursor."""

    def __init__(self, fauna_query: FaunaQuery):
        self.fauna_query = fauna_query

        # This read/write attribute specifies the number of rows to fetch at a
        # time with .fetchmany(). It defaults to 1 meaning to fetch a single
        # row at a time.
        self.arraysize = 1

        self.closed = False

        # this is updated only after a query
        self.description = None

        # this is set to a list of rows after a successful query
        self._results = None

    # Apparently mypy doesn't play nice with multiple decorators
    @property  # type: ignore
    @check_result
    @check_closed
    def rowcount(self):
        """Number of rows in the query results."""
        return len(self._results)

    @check_closed
    def close(self):
        """Close the cursor."""
        self.closed = True

    @check_closed
    def execute(self, operation, parameters=None):
        """Execute the query."""
        parameters = parameters or {}
        self.description = None
        query = apply_parameters(operation, parameters)

        self._results, self.description = self.fauna_query.execute(query)
        return self

    @check_closed
    def executemany(self, operation, seq_of_parameters=None):
        """Execute multiple queries."""
        raise exceptions.NotSupportedError(
            "`executemany` is not supported, use `execute` instead"
        )

    @check_result
    @check_closed
    def fetchone(self):
        """Fetch the next row of a query result set.

        Returns a single sequence, or `None` when no more data is available.
        """
        try:
            return self._results.pop(0)
        except IndexError:
            return None

    @check_result
    @check_closed
    def fetchmany(self, size=None):
        """Fetch the next set of rows of a query result.

        Returns rows as a sequence of sequences (e.g. a list of tuples).
        An empty sequence is returned when no more rows are available.
        """
        size = size or self.arraysize
        out = self._results[:size]
        self._results = self._results[size:]
        return out

    @check_result
    @check_closed
    def fetchall(self):
        """Fetch all (remaining) rows of a query result.

        Returns rows as a sequence of sequences (e.g. a list of tuples).
        Note that the cursor's arraysize attribute can affect the performance
        of this operation.
        """
        out = self._results[:]
        self._results = []
        return out

    @check_closed
    def setinputsizes(self, sizes):
        """Set output sizes.

        Not supported.
        """

    @check_closed
    def setoutputsizes(self, sizes):
        """Set output sizes.

        Not supported.
        """

    # Apparently mypy doesn't play nice with multiple decorators
    @property  # type: ignore
    @check_result
    @check_closed
    def lastrowid(self):
        """Return the last ID value inserted into current scope."""
        return self.fetchone()[0]

    @check_closed
    def __iter__(self):
        """Iterate through results."""
        return iter(self._results)
