import unittest
from unittest.mock import patch

from app.services.suggestion_service import (
    build_history_suggestions,
    get_name_suggestions,
    merge_suggestions,
)


class SuggestionServiceTests(unittest.TestCase):
    def test_merge_suggestions_deduplicates_by_qid(self):
        wikidata_items = [
            {"qid": "Q1", "label": "Alice", "description": "Author", "source": "wikidata"},
            {"qid": "Q2", "label": "Bob", "description": "Writer", "source": "wikidata"},
        ]
        history_items = [
            {"qid": "Q2", "label": "Bob from history", "description": "", "source": "history"},
            {"qid": "Q3", "label": "Carol", "description": "", "source": "history"},
        ]

        merged = merge_suggestions(wikidata_items, history_items, limit=5)

        self.assertEqual([item["qid"] for item in merged], ["Q1", "Q2", "Q3"])
        self.assertEqual(merged[1]["source"], "wikidata")

    def test_build_history_suggestions_filters_by_history_label_when_available(self):
        history = [
            {"start": "Q34660", "target": "Q173746"},
            {"start": "Q42", "target": "Q7251"},
        ]
        entity_summaries = {
            "Q34660": {"label": "J. K. Rowling", "description": "British author"},
            "Q173746": {"label": "Neil Gaiman", "description": "English writer"},
            "Q42": {"label": "Douglas Adams", "description": "English writer"},
            "Q7251": {"label": "Alan Turing", "description": "Computer scientist"},
        }

        suggestions = build_history_suggestions(history, query="row", limit=8, entity_summaries=entity_summaries)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["qid"], "Q34660")
        self.assertEqual(suggestions[0]["label"], "J. K. Rowling")
        self.assertEqual(suggestions[0]["description"], "British author")
        self.assertEqual(suggestions[0]["source"], "history")

    def test_get_name_suggestions_enriches_history_when_search_api_fails(self):
        history = [{"start": "Q34660", "target": "Q173746"}]
        entity_summaries = {
            "Q34660": {"label": "J. K. Rowling", "description": "British author"},
            "Q173746": {"label": "Neil Gaiman", "description": "English writer"},
        }

        with (
            patch("app.services.suggestion_service.get_history", return_value=history),
            patch(
                "app.services.suggestion_service.wikidata_client.get_entity_summaries",
                return_value=entity_summaries,
                create=True,
            ),
            patch("app.services.suggestion_service.wikidata_client.search_entities", side_effect=RuntimeError("boom")),
        ):
            suggestions = get_name_suggestions("gaim", limit=8)

        self.assertEqual(suggestions, [
            {
                "qid": "Q173746",
                "label": "Neil Gaiman",
                "description": "English writer",
                "source": "history",
            }
        ])


if __name__ == "__main__":
    unittest.main()
