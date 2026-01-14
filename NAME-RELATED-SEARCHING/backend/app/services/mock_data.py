from bfs_service import find_path

MOCK_GRAPH = {
    "A": ["B", "C"],
    "B": ["D"],
    "C": ["E"],
    "D": ["F"],
    "E": [],
    "F": []
}

def get_neighbors(node):
    return MOCK_GRAPH.get(node, [])

path = find_path("A", "F", get_neighbors, max_depth=4)
print(path)