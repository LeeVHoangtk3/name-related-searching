import unittest
import time

from app.services.bfs_service import find_path


class BfsLimitTests(unittest.TestCase):
    def test_find_path_respects_node_budget(self):
        def neighbors(node):
            if len(node) >= 6:
                return []
            return [f"{node}a", f"{node}b", f"{node}c"]

        path = find_path(
            start="S",
            target="TARGET",
            get_neighbors=neighbors,
            max_depth=10,
            max_nodes=30,
        )

        self.assertIsNone(path)

    def test_find_path_can_meet_from_both_sides(self):
        graph = {
            "A": ["B"],
            "B": [],
            "C": ["B"],
            "D": ["C"],
        }

        def neighbors(node):
            return graph.get(node, [])

        path = find_path(
            start="A",
            target="D",
            get_neighbors=neighbors,
            max_depth=6,
            max_nodes=100,
        )

        self.assertEqual(path, ["A", "B", "C", "D"])

    def test_find_path_respects_time_budget_inside_layer(self):
        def neighbors(node):
            if node == "S":
                return [f"N{i}" for i in range(60)]
            time.sleep(0.05)
            return []

        started_at = time.monotonic()
        path = find_path(
            start="S",
            target="T",
            get_neighbors=neighbors,
            max_depth=6,
            max_nodes=500,
            max_seconds=0.3,
        )
        elapsed = time.monotonic() - started_at

        self.assertIsNone(path)
        self.assertLess(elapsed, 0.5)


if __name__ == "__main__":
    unittest.main()
