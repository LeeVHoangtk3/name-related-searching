from collections import deque
from typing import Callable, List, Optional


def find_path(
    start: str,
    target: str,
    get_neighbors: Callable[[str], List[str]],
    max_depth: int = 3,
) -> Optional[List[str]]:
    queue = deque([(start, [start], 0)])
    visited = {start}

    while queue:
        current, path, depth = queue.popleft()
        if current == target:
            return path

        if depth >= max_depth:
            continue

        for n in get_neighbors(current):
            if n not in visited:
                visited.add(n)
                queue.append((n, path + [n], depth + 1))

    return None
