from collections import deque
from typing import Callable, Dict, List, Optional, AsyncGenerator
import time
import asyncio

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


class SearchLimitReached(Exception):
    pass


class SearchCancelled(Exception):
    pass


async def find_path(
    start: str,
    target: str,
    get_neighbors: Callable[[str], List[str]],
    max_depth: int,
    max_nodes: int = 15000,
    max_seconds: Optional[float] = None,
) -> AsyncGenerator[dict, None]:
    """
    Thuật toán BFS hai chiều bất đồng bộ (Async Generator) để tìm đường đi ngắn nhất.
    Liên tục phát (yield) trạng thái tiến độ thời gian thực về Route SSE.
    """
    if start == target:
        yield {"type": "complete", "path": [start]}
        return

    started_at = time.monotonic()
    forward_queue = deque([start])
    backward_queue = deque([target])

    forward_parent: Dict[str, Optional[str]] = {start: None}
    backward_parent: Dict[str, Optional[str]] = {target: None}
    forward_depth = {start: 0}
    backward_depth = {target: 0}

    def enforce_limits() -> None:
        explored_nodes = len(forward_parent) + len(backward_parent)
        if explored_nodes >= max_nodes:
            print(f"[WARN] BFS stopped at node limit={max_nodes}")
            raise SearchLimitReached
        if max_seconds is not None and time.monotonic() - started_at >= max_seconds:
            print(f"[WARN] BFS stopped at time limit={max_seconds}s")
            raise SearchLimitReached

    async def expand_one_layer(
        queue: deque,
        own_parent: Dict[str, Optional[str]],
        own_depth: Dict[str, int],
        other_parent: Dict[str, Optional[str]],
        other_depth: Dict[str, int],
    ) -> AsyncGenerator[dict, None]:
        for _ in range(len(queue)):
            enforce_limits()
            current = queue.popleft()
            current_depth = own_depth[current]

            yield {
                "type": "progress",
                "node_id": current,
                "total_explored": len(forward_parent) + len(backward_parent),
                "current_depth": current_depth,
                "elapsed_seconds": round(time.monotonic() - started_at, 2)
            }

            if current_depth >= max_depth:
                continue

            try:
                # Gọi hàm đồng bộ get_neighbors trong thread pool để không block event loop
                neighbors = await asyncio.to_thread(get_neighbors, current)
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
                    yield {"type": "found", "meeting": neighbor}
                    return

                queue.append(neighbor)

    try:
        while forward_queue or backward_queue:
            enforce_limits()

            meeting = None
            if forward_queue and (not backward_queue or len(forward_queue) <= len(backward_queue)):
                layer_gen = expand_one_layer(forward_queue, forward_parent, forward_depth, backward_parent, backward_depth)
                try:
                    async for val in layer_gen:
                        if val.get("type") == "found":
                            meeting = val.get("meeting")
                        else:
                            yield val
                finally:
                    await layer_gen.aclose()
            else:
                layer_gen = expand_one_layer(backward_queue, backward_parent, backward_depth, forward_parent, forward_depth)
                try:
                    async for val in layer_gen:
                        if val.get("type") == "found":
                            meeting = val.get("meeting")
                        else:
                            yield val
                finally:
                    await layer_gen.aclose()

            if meeting is not None:
                path = _build_path(meeting, forward_parent, backward_parent)
                yield {"type": "complete", "path": path}
                return

        yield {"type": "no_path"}
    except SearchLimitReached:
        yield {"type": "no_path"}
    except GeneratorExit:
        print("[INFO] BFS Generator closed via client cancellation. Releasing queues...")
        raise
    finally:
        # Giải phóng hoàn toàn bộ nhớ của các queue và map để chống OOM
        forward_queue.clear()
        backward_queue.clear()
        forward_parent.clear()
        backward_parent.clear()
        forward_depth.clear()
        backward_depth.clear()


def find_path_sync(
    start: str,
    target: str,
    get_neighbors: Callable[[str], List[str]],
    max_depth: int,
    max_nodes: int = 15000,
    max_seconds: Optional[float] = None,
    on_progress: Optional[Callable[[Dict], None]] = None,
) -> Optional[List[str]]:
    """
    Phiên bản đồng bộ của thuật toán BFS hai chiều (dành cho các endpoint REST truyền thống và unit tests).
    Có tích hợp giải phóng bộ nhớ triệt để trong block finally.
    """
    if start == target:
        return [start]

    started_at = time.monotonic()
    forward_queue = deque([start])
    backward_queue = deque([target])

    forward_parent: Dict[str, Optional[str]] = {start: None}
    backward_parent: Dict[str, Optional[str]] = {target: None}
    forward_depth = {start: 0}
    backward_depth = {target: 0}

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

    try:
        while forward_queue or backward_queue:
            enforce_limits()

            if forward_queue and (not backward_queue or len(forward_queue) <= len(backward_queue)):
                meeting = expand_one_layer(forward_queue, forward_parent, forward_depth, backward_parent, backward_depth)
            else:
                meeting = expand_one_layer(backward_queue, backward_parent, backward_depth, forward_parent, forward_depth)

            if meeting is not None:
                return _build_path(meeting, forward_parent, backward_parent)

        return None
    except SearchLimitReached:
        return None
    finally:
        # Giải phóng hoàn toàn bộ nhớ của các queue và map
        forward_queue.clear()
        backward_queue.clear()
        forward_parent.clear()
        backward_parent.clear()
        forward_depth.clear()
        backward_depth.clear()
