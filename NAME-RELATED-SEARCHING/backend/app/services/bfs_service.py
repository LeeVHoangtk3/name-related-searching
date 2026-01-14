from collections import deque
from typing import Callable, List, Optional
from neighbor_wikidata import get_neighbors

def find_path(start : str, 
              target : str, 
              get_neighbors : Callable[[str], List[str]], 
              max_depth : int
              ) -> Optional[List[str]] :
    
    queue = deque([(start, [start], 0)])
    visited = set([start])

    while queue:
        current, path, depth = queue.popleft()
        print(f"[BFS] Visiting {current}, depth={depth}")

        if current == target:
            return path

        if depth >= max_depth:
            continue

        try:
            neighbors = get_neighbors(current)
        except Exception as e:
            print(f"[WARN] Failed to get neighbors of {current}: {e}")
            continue

        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor], depth + 1))

    return None

if __name__ == "__main__":
    # Ví dụ test đơn giản (2 người liên quan gần)
    # J. K. Rowling = Q34660
    # Neil Gaiman = Q173746 (có khả năng liên hệ gần)

    start = "Q34660"     # J. K. Rowling
    target = "Q173746"   # Neil Gaiman

    print("Start BFS search...")
    path = find_path(
        start=start,
        target=target,
        get_neighbors=get_neighbors,
        max_depth=3,
    )

    if path:
        print("FOUND PATH:")
        print(" -> ".join(path))
    else:
        print("NO PATH FOUND")