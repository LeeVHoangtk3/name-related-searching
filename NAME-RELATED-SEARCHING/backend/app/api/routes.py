from fastapi import APIRouter, HTTPException, Query
from app.services.bfs_service import find_path
from app.services.neighbor_wikidata import get_neighbors
from app.core.redis import get_cache, set_cache, add_to_history, get_history

router = APIRouter()

@router.get("/search")
def search_path(
    start: str = Query(..., description="Wikidata ID của người bắt đầu"),
    target: str = Query(..., description="Wikidata ID của người đích"),
    max_depth: int = Query(3, description="Độ sâu tìm kiếm tối đa (mặc định là 3)")
):
    """
    Tìm kiếm đường nối ngắn nhất giữa hai thực thể Wikidata, có sử dụng Redis cache.
    Find the shortest path between two Wikidata entities, using Redis cache.
    """
    try:
        # 1. Kiểm tra cache Redis cho kết quả path
        cache_key = f"path:{start}:{target}"
        cached_path = get_cache(cache_key)
        
        if cached_path:
            add_to_history(start, target)
            return {"status": "success", "path": cached_path, "source": "cache"}

        # 2. Nếu không có cache, thực hiện BFS
        path = find_path(
            start=start,
            target=target,
            get_neighbors=get_neighbors,
            max_depth=max_depth
        )
        
        if not path:
            return {"status": "no_path", "path": []}
            
        # 3. Lưu kết quả vào cache và lịch sử toàn cục
        set_cache(cache_key, path)
        add_to_history(start, target)
        
        return {"status": "success", "path": path, "source": "api"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
