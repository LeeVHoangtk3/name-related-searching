import unittest
from unittest.mock import patch

from app.api.routes import get_suggestions


class SuggestionsApiTests(unittest.TestCase):
    def test_get_suggestions_returns_items(self):
        mocked_items = [
            {"qid": "Q34660", "label": "J. K. Rowling", "description": "British author", "source": "wikidata"}
        ]

        with patch("app.api.routes.get_name_suggestions", return_value=mocked_items, create=True):
            response = get_suggestions(q="row", limit=8)

        self.assertEqual(response, {"suggestions": mocked_items})


if __name__ == "__main__":
    unittest.main()
