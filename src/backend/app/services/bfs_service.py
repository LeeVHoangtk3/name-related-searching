import heapq
import time
import asyncio
from typing import Callable, Dict, List, Optional, AsyncGenerator

from app.services.embeddings import embedding_service

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
    Thuật toán tìm kiếm định hướng ngữ nghĩa Bi-directional A* bất đồng bộ (Async Generator).
    Sử dụng priority queues (heapq) và khoảng cách nhúng từ EmbeddingService.
    Liên tục phát (yield) trạng thái tiến độ thời gian thực về Route SSE.
    """
    if start == target:
        yield {"type": "complete", "path": [start]}
        return

    started_at = time.monotonic()
    
    # Hàng đợi ưu tiên lưu trữ bộ Tuple: (f_score, g_score, node)
    # Priority queues: stores (f_score, g_score, node)
    forward_heap = [(0.0, 0, start)]
    backward_heap = [(0.0, 0, target)]

    forward_parent = {start: None}
    backward_parent = {target: None}
    
    forward_g = {start: 0}
    backward_g = {target: 0}

    forward_closed = set()
    backward_closed = set()

    def enforce_limits() -> None:
        explored_nodes = len(forward_parent) + len(backward_parent)
        if explored_nodes >= max_nodes:
            print(f"[WARN] A* stopped at node limit={max_nodes}")
            raise SearchLimitReached
        if max_seconds is not None and time.monotonic() - started_at >= max_seconds:
            print(f"[WARN] A* stopped at time limit={max_seconds}s")
            raise SearchLimitReached

    try:
        meeting = None
        while forward_heap or backward_heap:
            enforce_limits()

            # Chọn nhánh mở rộng có f_score tối thiểu nhỏ nhất ở đầu heap
            if forward_heap and (not backward_heap or forward_heap[0][0] <= backward_heap[0][0]):
                # Expand Forward Branch
                f_score, current_g, current = heapq.heappop(forward_heap)
                if current in forward_closed:
                    continue
                forward_closed.add(current)
                
                current_depth = current_g
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
                    neighbors = await asyncio.to_thread(get_neighbors, current)
                except Exception as e:
                    print(f"[WARN] Failed to get neighbors of {current}: {e}")
                    continue

                # Tính Heuristic song song bằng ma trận NumPy
                try:
                    heuristics = embedding_service.calculate_heuristics(neighbors, target)
                except Exception as e:
                    print(f"[WARN] Heuristics calculation failed: {e}")
                    heuristics = {}

                new_g = current_depth + 1
                for neighbor in neighbors:
                    enforce_limits()
                    if neighbor not in forward_g or new_g < forward_g[neighbor]:
                        forward_g[neighbor] = new_g
                        forward_parent[neighbor] = current
                        
                        # Giao nhau giữa 2 nhánh
                        if neighbor in backward_parent:
                            if new_g + backward_g[neighbor] <= max_depth:
                                meeting = neighbor
                                break
                        
                        h = heuristics.get(neighbor, 1.0)
                        f = new_g + h
                        heapq.heappush(forward_heap, (f, new_g, neighbor))
                
                if meeting is not None:
                    break

            else:
                # Expand Backward Branch
                f_score, current_g, current = heapq.heappop(backward_heap)
                if current in backward_closed:
                    continue
                backward_closed.add(current)
                
                current_depth = current_g
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
                    neighbors = await asyncio.to_thread(get_neighbors, current)
                except Exception as e:
                    print(f"[WARN] Failed to get neighbors of {current}: {e}")
                    continue

                # Tính Heuristic song song bằng ma trận NumPy
                try:
                    heuristics = embedding_service.calculate_heuristics(neighbors, start)
                except Exception as e:
                    print(f"[WARN] Heuristics calculation failed: {e}")
                    heuristics = {}

                new_g = current_depth + 1
                for neighbor in neighbors:
                    enforce_limits()
                    if neighbor not in backward_g or new_g < backward_g[neighbor]:
                        backward_g[neighbor] = new_g
                        backward_parent[neighbor] = current
                        
                        # Giao nhau giữa 2 nhánh
                        if neighbor in forward_parent:
                            if new_g + forward_g[neighbor] <= max_depth:
                                meeting = neighbor
                                break
                        
                        h = heuristics.get(neighbor, 1.0)
                        f = new_g + h
                        heapq.heappush(backward_heap, (f, new_g, neighbor))
                
                if meeting is not None:
                    break

        if meeting is not None:
            path = _build_path(meeting, forward_parent, backward_parent)
            yield {"type": "complete", "path": path}
        else:
            yield {"type": "no_path"}

    except SearchLimitReached:
        yield {"type": "no_path"}
    except GeneratorExit:
        print("[INFO] A* Generator closed via client cancellation. Releasing memory structures...")
        raise
    finally:
        forward_heap.clear()
        backward_heap.clear()
        forward_parent.clear()
        backward_parent.clear()
        forward_g.clear()
        backward_g.clear()
        forward_closed.clear()
        backward_closed.clear()


def find_path_sync(
    start: str,
    target: str,
    get_neighbors: Callable[[str], List[str]],
    max_depth: int,
    max_nodes: int = 15000,
    max_seconds: Optional[float] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> Optional[List[str]]:
    """
    Phiên bản đồng bộ của thuật toán Bi-directional A* (dành cho REST endpoints và unit tests).
    """
    if start == target:
        return [start]

    started_at = time.monotonic()
    
    forward_heap = [(0.0, 0, start)]
    backward_heap = [(0.0, 0, target)]

    forward_parent = {start: None}
    backward_parent = {target: None}
    
    forward_g = {start: 0}
    backward_g = {target: 0}

    forward_closed = set()
    backward_closed = set()

    def enforce_limits() -> None:
        explored_nodes = len(forward_parent) + len(backward_parent)
        if explored_nodes >= max_nodes:
            raise SearchLimitReached
        if max_seconds is not None and time.monotonic() - started_at >= max_seconds:
            raise SearchLimitReached

    try:
        meeting = None
        while forward_heap or backward_heap:
            enforce_limits()

            if forward_heap and (not backward_heap or forward_heap[0][0] <= backward_heap[0][0]):
                f_score, current_g, current = heapq.heappop(forward_heap)
                if current in forward_closed:
                    continue
                forward_closed.add(current)
                
                current_depth = current_g
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

                try:
                    heuristics = embedding_service.calculate_heuristics(neighbors, target)
                except Exception as e:
                    print(f"[WARN] Heuristic calculations failed: {e}")
                    heuristics = {}

                new_g = current_depth + 1
                for neighbor in neighbors:
                    enforce_limits()
                    if neighbor not in forward_g or new_g < forward_g[neighbor]:
                        forward_g[neighbor] = new_g
                        forward_parent[neighbor] = current
                        
                        if neighbor in backward_parent:
                            if new_g + backward_g[neighbor] <= max_depth:
                                meeting = neighbor
                                break
                        
                        h = heuristics.get(neighbor, 1.0)
                        f = new_g + h
                        heapq.heappush(forward_heap, (f, new_g, neighbor))
                
                if meeting is not None:
                    break

            else:
                f_score, current_g, current = heapq.heappop(backward_heap)
                if current in backward_closed:
                    continue
                backward_closed.add(current)
                
                current_depth = current_g
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

                try:
                    heuristics = embedding_service.calculate_heuristics(neighbors, start)
                except Exception as e:
                    print(f"[WARN] Heuristic calculations failed: {e}")
                    heuristics = {}

                new_g = current_depth + 1
                for neighbor in neighbors:
                    enforce_limits()
                    if neighbor not in backward_g or new_g < backward_g[neighbor]:
                        backward_g[neighbor] = new_g
                        backward_parent[neighbor] = current
                        
                        if neighbor in forward_parent:
                            if new_g + forward_g[neighbor] <= max_depth:
                                meeting = neighbor
                                break
                        
                        h = heuristics.get(neighbor, 1.0)
                        f = new_g + h
                        heapq.heappush(backward_heap, (f, new_g, neighbor))
                
                if meeting is not None:
                    break

        if meeting is not None:
            return _build_path(meeting, forward_parent, backward_parent)
        return None

    except SearchLimitReached:
        return None
    finally:
        forward_heap.clear()
        backward_heap.clear()
        forward_parent.clear()
        backward_parent.clear()
        forward_g.clear()
        backward_g.clear()
        forward_closed.clear()
        backward_closed.clear()
