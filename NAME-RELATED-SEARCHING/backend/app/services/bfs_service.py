from collections import deque
from typing import Callable, Dict, List, Optional
import time
from app.services.neighbor_wikidata import get_neighbors


def _build_path(meeting: str, forward_parent: Dict[str, Optional[str]], backward_parent: Dict[str, Optional[str]]) -> List[str]:
    forward_path: List[str] = []
    node: Optional[str] = meeting
    while node is not None:
        forward_path.append(node)
        node = forward_parent[node]
    forward_path.reverse()

    backward_path: List[str] = []
    node = backward_parent[meeting]
    while node is not None:
        backward_path.append(node)
        node = backward_parent[node]

    return forward_path + backward_path


def find_path(
    start: str,
    target: str,
    get_neighbors: Callable[[str], List[str]],
    max_depth: int,
    max_nodes: int = 15000,
    max_seconds: Optional[float] = None,
    on_progress: Optional[Callable[[Dict], None]] = None,
) -> Optional[List[str]]:
    if start == target:
        return [start]

    started_at = time.monotonic()
    forward_queue = deque([start])
    backward_queue = deque([target])

    forward_parent: Dict[str, Optional[str]] = {start: None}
    backward_parent: Dict[str, Optional[str]] = {target: None}
    forward_depth = {start: 0}
    backward_depth = {target: 0}

    class SearchLimitReached(Exception):
        pass

    def enforce_limits() -> None:
        explored_nodes = len(forward_parent) + len(backward_parent)
        if explored_nodes >= max_nodes:
            print(f"[WARN] BFS stopped at node limit={max_nodes}")
            raise SearchLimitReached
        if max_seconds is not None and time.monotonic() - started_at >= max_seconds:
            print(f"[WARN] BFS stopped at time limit={max_seconds}s")
            raise SearchLimitReached

    def expand_one_layer(
        queue: deque,
        own_parent: Dict[str, Optional[str]],
        own_depth: Dict[str, int],
        other_parent: Dict[str, Optional[str]],
        other_depth: Dict[str, int],
    ) -> Optional[str]:
        for _ in range(len(queue)):
            enforce_limits()
            current = queue.popleft()
            current_depth = own_depth[current]

            if on_progress:
                on_progress({
                    "node_id": current,
                    "total_explored": len(forward_parent) + len(backward_parent),
                    "current_depth": current_depth,
                    "elapsed_seconds": round(time.monotonic() - started_at, 2)
                })

            if current_depth >= max_depth:
                continue

            try:
                neighbors = get_neighbors(current)
            except Exception as e:
                print(f"[WARN] Failed to get neighbors of {current}: {e}")
                continue

            for neighbor in neighbors:
                enforce_limits()
                if neighbor in own_parent:
                    continue

                depth = current_depth + 1
                own_parent[neighbor] = current
                own_depth[neighbor] = depth

                if neighbor in other_parent and depth + other_depth[neighbor] <= max_depth:
                    return neighbor

                queue.append(neighbor)
        return None

    while forward_queue or backward_queue:
        try:
            enforce_limits()
        except SearchLimitReached:
            return None

        try:
            if forward_queue and (not backward_queue or len(forward_queue) <= len(backward_queue)):
                meeting = expand_one_layer(forward_queue, forward_parent, forward_depth, backward_parent, backward_depth)
            else:
                meeting = expand_one_layer(backward_queue, backward_parent, backward_depth, forward_parent, forward_depth)
        except SearchLimitReached:
            return None

        if meeting is not None:
            return _build_path(meeting, forward_parent, backward_parent)

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
