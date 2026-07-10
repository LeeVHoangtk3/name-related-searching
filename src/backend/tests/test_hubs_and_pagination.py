import unittest
import json
import redis
from unittest.mock import patch, MagicMock
from app.core.redis import get_history_paginated, _memory_history
from app.api.routes import get_global_history
from app.services.neighbor_wikidata import get_neighbors
from app.services.cache_syncer import prefetch_hub_neighbors

class HubsAndPaginationTests(unittest.TestCase):
    def setUp(self):
        _memory_history.clear()

    @patch("app.core.redis.redis_client.llen", side_effect=redis.exceptions.ConnectionError("Mock Connection Error"))
    def test_get_history_paginated_fallback(self, mock_llen):
        # Populate mock memory history
        for i in range(15):
            _memory_history.append({"start": f"Q{i}", "target": f"Q{i+1}"})

        # Test page 1, size 10
        total, items = get_history_paginated(1, 10)
        self.assertEqual(total, 15)
        self.assertEqual(len(items), 10)
        self.assertEqual(items[0], {"start": "Q0", "target": "Q1"})

        # Test page 2, size 10
        total, items = get_history_paginated(2, 10)
        self.assertEqual(total, 15)
        self.assertEqual(len(items), 5)
        self.assertEqual(items[0], {"start": "Q10", "target": "Q11"})

    @patch("app.api.routes.get_history_paginated")
    def test_routes_history_endpoint_metadata(self, mock_get_history):
        mock_items = [{"start": "Q1", "target": "Q2"}]
        mock_get_history.return_value = (25, mock_items)

        # Call endpoint handler directly
        response = get_global_history(page=2, size=10)
        
        self.assertIn("metadata", response)
        self.assertIn("history", response)
        self.assertEqual(response["metadata"]["total_items"], 25)
        self.assertEqual(response["metadata"]["current_page"], 2)
        self.assertEqual(response["metadata"]["size"], 10)
        self.assertEqual(response["metadata"]["total_pages"], 3)
        self.assertEqual(response["history"], mock_items)

    @patch("app.services.neighbor_wikidata.get_cache")
    @patch("app.services.neighbor_wikidata.wikidata_client.query")
    def test_get_neighbors_hub_cache_hit(self, mock_query, mock_get_cache):
        # Q5 is human (Hub)
        mock_get_cache.return_value = ["Q1", "Q2", "Q3", "Q4", "Q5"]

        neighbors = get_neighbors("Q5", limit=3)
        
        # Must fetch from hub_cache:Q5 first
        mock_get_cache.assert_called_with("hub_cache:Q5")
        self.assertEqual(neighbors, ["Q1", "Q2", "Q3"])
        # Wikidata query should not be called since cache hit
        mock_query.assert_not_called()

    @patch("app.services.cache_syncer.redis_client.set")
    @patch("app.services.cache_syncer.wikidata_client.query")
    def test_prefetch_hub_neighbors(self, mock_query, mock_redis_set):
        mock_query.return_value = [
            {"neighbor": {"value": "http://www.wikidata.org/entity/Q100"}},
            {"neighbor": {"value": "http://www.wikidata.org/entity/Q200"}}
        ]

        import asyncio
        asyncio.run(prefetch_hub_neighbors("Q5"))

        # Verify SPARQL query ran
        mock_query.assert_called_once()
        # Verify cached in Redis with TTL 24h
        mock_redis_set.assert_called_once()
        args, kwargs = mock_redis_set.call_args
        self.assertEqual(args[0], "hub_cache:Q5")
        self.assertEqual(json.loads(args[1]), ["Q100", "Q200"])
        self.assertEqual(kwargs.get("ex"), 24 * 3600)

if __name__ == "__main__":
    unittest.main()
