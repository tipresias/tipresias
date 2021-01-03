"""DBAPI for use in the FaunaDialect."""

from faunadb.client import FaunaClient

from tipping.db.sqlalchemy_fauna import exceptions


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


class FaunaConnection:
    """Connection to a Fauna DB instance."""

    def __init__(self, host="", port=None, secret="", scheme=""):
        self.client = FaunaClient(scheme=scheme, domain=host, port=port, secret=secret)
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
    def cursor(self):
        """Return a new Cursor Object using the connection."""
        cursor = FaunaCursor()
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


def _execute_query(_operation, _parameters):
    return [("empty",)], "To be implemented"


class FaunaCursor:
    """Fauna connection cursor."""

    def __init__(self):
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

        self._results, self.description = _execute_query(operation, parameters)
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

    @check_closed
    def __iter__(self):
        """Iterate through results."""
        return iter(self._results)
