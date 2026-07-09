import unittest
from unittest.mock import patch, MagicMock
from app.services.embeddings import embedding_service
from app.services.bfs_service import find_path_sync, find_path
from app.services.graph_config import BLACKLIST_PROPERTIES
from app.services.neighbor_wikidata import build_neighbor_query
from app.services.path_service import find_path_in_memgraph, is_path_stale

class AStarAndGraphDBTests(unittest.TestCase):

    def test_embedding_service_deterministic(self):
        v1 = embedding_service.get_vector("Q5")
        v2 = embedding_service.get_vector("Q5")
        v3 = embedding_service.get_vector("Q30")

        # Must return the same vector for the same QID
        import numpy as np
        np.testing.assert_array_almost_equal(v1, v2)
        # Norm should be 1.0 (unit vector)
        self.assertAlmostEqual(float(np.linalg.norm(v1)), 1.0, places=5)
        # Vector for different QID should be different
        self.assertNotEqual(float(np.dot(v1, v3)), 1.0)

    def test_embedding_service_vectorized_heuristics(self):
        nodes = ["Q5", "Q30", "Q571"]
        heuristics = embedding_service.calculate_heuristics(nodes, "Q5")

        self.assertEqual(len(heuristics), 3)
        # h(Q5) to target Q5 must be 0.0 (cosine similarity of same vector is 1.0, so 1.0 - 1.0 = 0.0)
        self.assertAlmostEqual(heuristics["Q5"], 0.0, places=5)
        # Other nodes should be > 0.0
        self.assertGreater(heuristics["Q30"], 0.0)
        self.assertGreater(heuristics["Q571"], 0.0)

    def test_build_neighbor_query_applies_blacklist(self):
        query = build_neighbor_query("Q100")
        
        # Verify blacklist filtering query exists in constructed SPARQL
        self.assertIn("FILTER(?p NOT IN", query)
        for prop in BLACKLIST_PROPERTIES:
            self.assertIn(f"wdt:{prop}", query)

    def test_astar_finds_path_sync(self):
        # Mock graph: Q1 -> Q2 -> Q3
        graph = {
            "Q1": ["Q2"],
            "Q2": ["Q3", "Q1"],
            "Q3": ["Q2"]
        }

        def mock_get_neighbors(node):
            return graph.get(node, [])

        path = find_path_sync(
            start="Q1",
            target="Q3",
            get_neighbors=mock_get_neighbors,
            max_depth=4
        )

        self.assertEqual(path, ["Q1", "Q2", "Q3"])

    @patch("app.services.path_service.get_db_session", return_value=None)
    def test_find_path_in_memgraph_fallback(self, mock_get_session):
        # If driver is None or not connected, must return None gracefully
        path = find_path_in_memgraph("Q1", "Q3", max_depth=4)
        self.assertIsNone(path)

    @patch("app.services.path_service.get_db_session", return_value=None)
    def test_is_path_stale_fallback(self, mock_get_session):
        # Default behavior when driver is None should be True (force update)
        stale = is_path_stale(["Q1", "Q2"])
        self.assertTrue(stale)

if __name__ == "__main__":
    unittest.main()
