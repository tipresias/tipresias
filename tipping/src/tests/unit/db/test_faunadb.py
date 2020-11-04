# pylint: disable=missing-docstring

from unittest import TestCase
from unittest.mock import patch

from tipping.db.faunadb import FaunadbClient


class TestFaunaDBClient(TestCase):
    def setUp(self):

        self.client = FaunadbClient(faunadb_key="notakey")

    @patch("tipping.db.faunadb.requests.post")
    def test_import(self, mock_post):
        self.client.import_schema()

        # It posts to FaunaDB
        mock_post.assert_called()
        # It sends the schema file
        isinstance(mock_post.mock_calls[0].kwargs["data"], bytes)

    @patch("tipping.db.faunadb.Client.execute")
    def test_graphql(self, mock_execute):
        mock_data = {"createTeam": {"name": "NewTeam"}}
        mock_execute.return_value = mock_data

        query = """
            mutation {
                createTeam(data: { name: "NewTeam" }) { name }
            }
        """

        data = self.client.graphql(query)

        # It returns the GQL query data
        self.assertEqual(data, mock_data)

        with self.subTest("when there are errors"):
            mock_errors = {
                "errors": [
                    {
                        "message": "Oops",
                        "extensions": {"code": "That boy ain't right"},
                    }
                ]
            }
            mock_execute.return_value = mock_errors

            with self.assertRaisesRegex(Exception, r"Oops"):
                self.client.graphql(query)
