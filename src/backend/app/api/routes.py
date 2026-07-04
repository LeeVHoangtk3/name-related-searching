import re
import json
from functools import partial
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse
from app.clients.wikidata import wikidata_client
from app.services.bfs_service import find_path, find_path_sync
from app.services.neighbor_wikidata import get_neighbors
from app.services.suggestion_service import get_name_suggestions
from app.core.redis import get_cache, set_cache, add_to_history, get_history
from app.services.normalize import minimize_graph_payload

router = APIRouter()
QID_PATTERN = re.compile(r"^Q\d+$", re.IGNORECASE)
FAST_DEPTH = 6
FAST_NEIGHBOR_LIMIT = 20
FAST_MAX_NODES = 6000
FAST_QUERY_TIMEOUT = 6
DEEP_NEIGHBOR_LIMIT = 50
DEEP_MAX_NODES = 15000
DEEP_QUERY_TIMEOUT = 12


def build_path_cache_key(start_id: str, target_id: str, mode: str, effective_depth: int) -> str:
    return f"path:{start_id}:{target_id}:{mode}:{effective_depth}"


def resolve_search_config(mode: str, max_depth: int):
    if mode == "fast":
        effective_depth = min(max_depth, FAST_DEPTH)
        return (
            effective_depth,
            partial(
                get_neighbors,
                limit=FAST_NEIGHBOR_LIMIT,
                timeout=FAST_QUERY_TIMEOUT,
            ),
            FAST_MAX_NODES,
            None,
        )

    return (
        max_depth,
        partial(
            get_neighbors,
            limit=DEEP_NEIGHBOR_LIMIT,
            timeout=DEEP_QUERY_TIMEOUT,
        ),
        DEEP_MAX_NODES,
        None,
    )


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

        effective_depth, neighbor_fetcher, max_nodes, max_seconds = resolve_search_config(mode, max_depth)

        # 1. Kiểm tra cache Redis cho kết quả path
        cache_key = build_path_cache_key(start_id, target_id, mode, effective_depth)
        cached_path = get_cache(cache_key)
        
        if cached_path:
            add_to_history(start_id, target_id)
            return {"status": "success", "path": cached_path, "source": "cache"}

        # 2. Nếu không có cache, thực hiện BFS
        path = find_path_sync(
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

@router.get("/search/stream")
async def search_path_stream(
    start: str = Query(..., description="Wikidata ID của người bắt đầu"),
    target: str = Query(..., description="Wikidata ID của người đích"),
    max_depth: int = Query(8, ge=1, le=10, description="Độ sâu tìm kiếm tối đa"),
    mode: str = Query("fast", pattern="^(fast|deep)$", description="Chế độ tìm kiếm: fast hoặc deep"),
    request: Request = None,
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
        effective_depth, neighbor_fetcher, max_nodes, _ = resolve_search_config(mode, max_depth)

        # 1. Check Redis cache first
        cache_key = build_path_cache_key(start_id, target_id, mode, effective_depth)
        cached_path = get_cache(cache_key)
        if cached_path:
            add_to_history(start_id, target_id)
            # Tối ưu hóa: Rút gọn dữ liệu phẳng trả về
            graph_payload = minimize_graph_payload(cached_path)
            yield {
                "event": "complete",
                "data": json.dumps({"status": "success", "graph": graph_payload, "source": "cache"})
            }
            return

        # 2. Tạo generator async BFS
        bfs_gen = find_path(
            start=start_id,
            target=target_id,
            get_neighbors=neighbor_fetcher,
            max_depth=effective_depth,
            max_nodes=max_nodes,
        )

        try:
            async for update in bfs_gen:
                # Kiểm tra client disconnect định kỳ
                if request is not None and await request.is_disconnected():
                    print("[INFO] Client disconnected. Aborting BFS.")
                    break

                if update["type"] == "progress":
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "node_id": update["node_id"],
                            "total_explored": update["total_explored"],
                            "current_depth": update["current_depth"],
                            "elapsed_seconds": update["elapsed_seconds"]
                        })
                    }
                elif update["type"] == "complete":
                    path = update["path"]
                    set_cache(cache_key, path)
                    add_to_history(start_id, target_id)
                    # Tối ưu hóa: Rút gọn dữ liệu phẳng trả về
                    graph_payload = minimize_graph_payload(path)
                    yield {
                        "event": "complete",
                        "data": json.dumps({"status": "success", "graph": graph_payload, "source": "api"})
                    }
                    return
                elif update["type"] == "no_path":
                    result = {
                        "status": "no_path", 
                        "graph": {"nodes": [], "links": []}, 
                        "mode": mode
                    }
                    if mode == "fast":
                        result["suggestion"] = "Retry with mode=deep for broader search."
                    yield {
                        "event": "complete",
                        "data": json.dumps(result)
                    }
                    return
        except GeneratorExit:
            print("[INFO] SSE stream generator exit (GeneratorExit). Closing BFS generator.")
            raise
        finally:
            # Đóng generator BFS để kích hoạt khối finally giải phóng bộ nhớ bên trong nó
            await bfs_gen.aclose()

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
