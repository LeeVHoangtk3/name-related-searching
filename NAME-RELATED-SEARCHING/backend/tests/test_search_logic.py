import unittest
from unittest.mock import patch

from app.api.routes import search_path
from app.services.neighbor_wikidata import build_neighbor_query


class SearchLogicTests(unittest.TestCase):
    def test_build_neighbor_query_includes_incoming_and_outgoing_edges_for_any_wikidata_item(self):
        query = build_neighbor_query("Q42", limit=50)
        self.assertIn("wd:Q42 ?p ?neighbor", query)
        self.assertIn("?neighbor ?p wd:Q42", query)
        self.assertIn('STRSTARTS(STR(?neighbor), "http://www.wikidata.org/entity/Q")', query)
        self.assertNotIn("wdt:P31 wd:Q5", query)

    def test_search_path_defaults_to_fast_mode_limits_and_constraint_aware_cache_key(self):
        with (
            patch("app.api.routes.resolve_entity_input", side_effect=lambda value: value, create=True),
            patch("app.api.routes.get_cache", return_value=None) as mock_get_cache,
            patch("app.api.routes.find_path", return_value=None) as mock_find_path,
            patch("app.api.routes.set_cache"),
            patch("app.api.routes.add_to_history"),
        ):
            response = search_path(start="Q1", target="Q2", max_depth=8, mode="fast")

        self.assertEqual(response["status"], "no_path")
        mock_get_cache.assert_called_once_with("path:Q1:Q2:fast:6")
        self.assertEqual(mock_find_path.call_args.kwargs["max_depth"], 6)
        self.assertEqual(mock_find_path.call_args.kwargs["max_nodes"], 6000)
        self.assertIsNone(mock_find_path.call_args.kwargs["max_seconds"])
        self.assertEqual(mock_find_path.call_args.kwargs["get_neighbors"].keywords["limit"], 20)
        self.assertEqual(mock_find_path.call_args.kwargs["get_neighbors"].keywords["timeout"], 6)

    def test_search_path_deep_mode_uses_requested_limits_and_constraint_aware_cache_key(self):
        with (
            patch("app.api.routes.resolve_entity_input", side_effect=lambda value: value, create=True),
            patch("app.api.routes.get_cache", return_value=None) as mock_get_cache,
            patch("app.api.routes.find_path", return_value=["Q1", "Q2"]) as mock_find_path,
            patch("app.api.routes.set_cache") as mock_set_cache,
            patch("app.api.routes.add_to_history"),
        ):
            response = search_path(start="Q1", target="Q2", max_depth=9, mode="deep")

        self.assertEqual(response["status"], "success")
        mock_get_cache.assert_called_once_with("path:Q1:Q2:deep:9")
        self.assertEqual(mock_find_path.call_args.kwargs["max_depth"], 9)
        self.assertEqual(mock_find_path.call_args.kwargs["max_nodes"], 15000)
        self.assertIsNone(mock_find_path.call_args.kwargs["max_seconds"])
        self.assertEqual(mock_find_path.call_args.kwargs["get_neighbors"].keywords["limit"], 50)
        self.assertEqual(mock_find_path.call_args.kwargs["get_neighbors"].keywords["timeout"], 12)
        mock_set_cache.assert_called_once_with("path:Q1:Q2:deep:9", ["Q1", "Q2"])

    def test_resolve_entity_input_maps_name_to_qid(self):
        from app.api.routes import resolve_entity_input

        with patch(
            "app.api.routes.wikidata_client.search_entities",
            return_value=[{"qid": "Q22686", "label": "Donald Trump"}],
            create=True,
        ):
            resolved = resolve_entity_input("trump")

        self.assertEqual(resolved, "Q22686")


if __name__ == "__main__":
    unittest.main()
