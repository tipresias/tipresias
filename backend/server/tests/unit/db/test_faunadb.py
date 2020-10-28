# pylint: disable=missing-docstring

from unittest import TestCase
from unittest.mock import patch

from server.db.faunadb import FaunadbClient


class TestFaunaDBClient(TestCase):
    @patch("server.db.faunadb.requests.post")
    def test_import(self, mock_post):
        FaunadbClient.import_schema()

        # It posts to FaunaDB
        mock_post.assert_called()
        # It sends the schema file
        isinstance(mock_post.mock_calls[0].kwargs["data"], bytes)
