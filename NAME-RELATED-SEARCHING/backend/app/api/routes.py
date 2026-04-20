import re
import asyncio
import json
from functools import partial
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from app.clients.wikidata import wikidata_client
from app.services.bfs_service import find_path
from app.services.neighbor_wikidata import get_neighbors
from app.services.suggestion_service import get_name_suggestions
from app.core.redis import get_cache, set_cache, add_to_history, get_history

router = APIRouter()
QID_PATTERN = re.compile(r"^Q\d+$", re.IGNORECASE)
FAST_DEPTH = 6
FAST_NEIGHBOR_LIMIT = 20
FAST_MAX_NODES = 6000
FAST_QUERY_TIMEOUT = 6
DEEP_NEIGHBOR_LIMIT = 50
DEEP_MAX_NODES = 15000
DEEP_QUERY_TIMEOUT = 12


def resolve_entity_input(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return normalized
    if QID_PATTERN.match(normalized):
        return normalized.upper()

    candidates = wikidata_client.search_entities(normalized, limit=1)
    if candidates:
        resolved_qid = str(candidates[0].get("qid", "")).strip()
        if QID_PATTERN.match(resolved_qid):
            return resolved_qid.upper()
    return normalized

@router.get("/search")
def search_path(
    start: str = Query(..., description="Wikidata ID của người bắt đầu"),
    target: str = Query(..., description="Wikidata ID của người đích"),
    max_depth: int = Query(8, ge=1, le=10, description="Độ sâu tìm kiếm tối đa"),
    mode: str = Query("fast", pattern="^(fast|deep)$", description="Chế độ tìm kiếm: fast hoặc deep"),
):
    """
    Tìm kiếm đường nối ngắn nhất giữa hai thực thể Wikidata, có sử dụng Redis cache.
    Find the shortest path between two Wikidata entities, using Redis cache.
    """
    try:
        start_id = resolve_entity_input(start)
        target_id = resolve_entity_input(target)
        if not QID_PATTERN.match(start_id) or not QID_PATTERN.match(target_id):
            raise HTTPException(
                status_code=400,
                detail="start/target must be a Wikidata QID or a resolvable entity name.",
            )

        # 1. Kiểm tra cache Redis cho kết quả path
        cache_key = f"path:{start_id}:{target_id}"
        cached_path = get_cache(cache_key)
        
        if cached_path:
            add_to_history(start_id, target_id)
            return {"status": "success", "path": cached_path, "source": "cache"}

        if mode == "fast":
            effective_depth = min(max_depth, FAST_DEPTH)
            neighbor_fetcher = partial(
                get_neighbors,
                limit=FAST_NEIGHBOR_LIMIT,
                timeout=FAST_QUERY_TIMEOUT,
            )
            max_nodes = FAST_MAX_NODES
            max_seconds = None
        else:
            effective_depth = max_depth
            neighbor_fetcher = partial(
                get_neighbors,
                limit=DEEP_NEIGHBOR_LIMIT,
                timeout=DEEP_QUERY_TIMEOUT,
            )
            max_nodes = DEEP_MAX_NODES
            max_seconds = None

        # 2. Nếu không có cache, thực hiện BFS
        path = find_path(
            start=start_id,
            target=target_id,
            get_neighbors=neighbor_fetcher,
            max_depth=effective_depth,
            max_nodes=max_nodes,
            max_seconds=max_seconds,
        )
        
        if not path:
            response = {"status": "no_path", "path": [], "mode": mode}
            if mode == "fast":
                response["suggestion"] = "Retry with mode=deep for broader search."
            return response
            
        # 3. Lưu kết quả vào cache và lịch sử toàn cục
        set_cache(cache_key, path)
        add_to_history(start_id, target_id)
        
        return {"status": "success", "path": path, "source": "api"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/stream")
async def search_path_stream(
    start: str = Query(..., description="Wikidata ID của người bắt đầu"),
    target: str = Query(..., description="Wikidata ID của người đích"),
    max_depth: int = Query(8, ge=1, le=10, description="Độ sâu tìm kiếm tối đa"),
    mode: str = Query("fast", pattern="^(fast|deep)$", description="Chế độ tìm kiếm: fast hoặc deep"),
):
    """
    SSE stream version of search_path to provide real-time progress updates.
    """
    start_id = resolve_entity_input(start)
    target_id = resolve_entity_input(target)

    if not QID_PATTERN.match(start_id) or not QID_PATTERN.match(target_id):
        raise HTTPException(
            status_code=400,
            detail="start/target must be a Wikidata QID or a resolvable entity name.",
        )

    async def event_generator() -> AsyncGenerator[dict, None]:
        # 1. Check Redis cache first
        cache_key = f"path:{start_id}:{target_id}"
        cached_path = get_cache(cache_key)
        if cached_path:
            add_to_history(start_id, target_id)
            yield {
                "event": "complete",
                "data": json.dumps({"status": "success", "path": cached_path, "source": "cache"})
            }
            return

        # 2. Setup BFS parameters
        if mode == "fast":
            effective_depth = min(max_depth, FAST_DEPTH)
            neighbor_fetcher = partial(
                get_neighbors,
                limit=FAST_NEIGHBOR_LIMIT,
                timeout=FAST_QUERY_TIMEOUT,
            )
            max_nodes = FAST_MAX_NODES
        else:
            effective_depth = max_depth
            neighbor_fetcher = partial(
                get_neighbors,
                limit=DEEP_NEIGHBOR_LIMIT,
                timeout=DEEP_QUERY_TIMEOUT,
            )
            max_nodes = DEEP_MAX_NODES

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_progress_callback(update_data: dict):
            # This runs in the BFS thread, use the captured loop to put in the queue
            print(f"[PROGRESS] {update_data['node_id']} | Total: {update_data['total_explored']}")
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "progress", "data": json.dumps(update_data)})

        def run_bfs():
            try:
                print(f"[INFO] Starting BFS from {start_id} to {target_id}")
                path = find_path(
                    start=start_id,
                    target=target_id,
                    get_neighbors=neighbor_fetcher,
                    max_depth=effective_depth,
                    max_nodes=max_nodes,
                    on_progress=on_progress_callback
                )
                
                if path:
                    print(f"[INFO] BFS Found path: {' -> '.join(path)}")
                    set_cache(cache_key, path)
                    add_to_history(start_id, target_id)
                    result = {"status": "success", "path": path, "source": "api"}
                else:
                    print(f"[INFO] BFS No path found.")
                    result = {"status": "no_path", "path": [], "mode": mode}
                    if mode == "fast":
                        result["suggestion"] = "Retry with mode=deep for broader search."
                
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "complete", "data": json.dumps(result)})
            except Exception as e:
                print(f"[ERROR] BFS Error: {e}")
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "data": json.dumps({"detail": str(e)})})

        # Start BFS in a separate thread
        bfs_task = loop.run_in_executor(None, run_bfs)

        while True:
            event = await queue.get()
            yield event
            if event["event"] in ["complete", "error"]:
                break
        
        await bfs_task

    return EventSourceResponse(event_generator())

@router.get("/history")
def get_global_history():
    """
    Lấy danh sách lịch sử tìm kiếm toàn cục từ Redis.
    Get global search history from Redis.
    """
    try:
        history = get_history()
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/neighbors/{wikidata_id}")
def get_entity_neighbors(wikidata_id: str):
    """
    Lấy danh sách các thực thể lân cận của một Wikidata ID.
    Get list of neighbor entities for a Wikidata ID.
    """
    try:
        neighbors = get_neighbors(wikidata_id)
        return {"wikidata_id": wikidata_id, "neighbors": neighbors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
def get_suggestions(
    q: str = Query(..., description="Từ khóa gợi ý tên"),
    limit: int = Query(8, ge=1, le=20, description="Số lượng gợi ý tối đa"),
):
    """
    Lấy danh sách gợi ý tên/QID từ Wikidata và lịch sử tìm kiếm.
    Get name/QID suggestions from Wikidata and search history.
    """
    try:
        suggestions = get_name_suggestions(q, limit)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
