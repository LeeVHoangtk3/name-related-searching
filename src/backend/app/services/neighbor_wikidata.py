from typing import List, Optional
from app.clients.wikidata import wikidata_client
from app.core.config import settings
from app.core.redis import get_cache, set_cache
from app.services.file_cache import get_cache as get_file_cache, set_cache as set_file_cache

def build_neighbor_query(wikidata_id: str, limit: int = settings.DEFAULT_LIMIT) -> str:
    """
    Xây dựng câu truy vấn SPARQL tối ưu để tìm các thực thể lân cận.
    Sử dụng isURI(?neighbor) thay vì STRSTARTS(STR(?neighbor), ...) để tối ưu index.
    """
    return f"""
    SELECT DISTINCT ?neighbor WHERE {{
      {{
        wd:{wikidata_id} ?p ?neighbor .
        FILTER(isURI(?neighbor))
      }}
      UNION
      {{
        ?neighbor ?p wd:{wikidata_id} .
        FILTER(isURI(?neighbor))
      }}
      FILTER(?neighbor != wd:{wikidata_id})
    }}
    LIMIT {limit}
    """

def get_neighbors(
    wikidata_id: str,
    limit: int = settings.DEFAULT_LIMIT,
    timeout: Optional[int] = None,
) -> List[str]:
    """
    Lấy danh sách ID của các thực thể lân cận từ Wikidata, có sử dụng Redis cache.
    Get a list of IDs of neighbor entities from Wikidata, using Redis cache.
    """
    # Chốt chặn kiểm tra Hubs cache để chống rate-limiting và timeouts
    # Hubs cache gate to prevent rate-limiting and connection timeouts
    strategic_hubs = {"Q5", "Q30", "Q571", "Q11424", "Q4830453"}
    if wikidata_id in strategic_hubs:
        hub_cached = get_cache(f"hub_cache:{wikidata_id}")
        if hub_cached is not None:
            print(f"[INFO] Hub Cache Hit for {wikidata_id}")
            return hub_cached[:limit]

    cache_key = f"neighbors:{wikidata_id}:{limit}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    query = build_neighbor_query(wikidata_id, limit=limit)
    bindings = wikidata_client.query(query, timeout=timeout)

    neighbors: List[str] = []
    for item in bindings:
        if "neighbor" in item and "value" in item["neighbor"]:
            uri = item["neighbor"]["value"]
            neighbors.append(uri.split("/")[-1])

    # Lưu vào cache trong 48 giờ
    # Save to cache for 48 hours
    set_cache(cache_key, neighbors, expire=172800)
    
    return neighbors

def get_entity_type(wikidata_id: str) -> List[str]:
    """
    Lấy danh sách các lớp (P31 - instance of) của thực thể Wikidata.
    Sử dụng file cache cục bộ (entity_type.json) để tăng tốc độ truy vấn.
    """
    cache_key = f"entity_type:{wikidata_id}"
    cached = get_file_cache("entity_type.json", cache_key)
    if cached is not None:
        return cached

    query = f"""
    SELECT ?type WHERE {{
      wd:{wikidata_id} wdt:P31 ?type .
    }}
    """
    try:
        bindings = wikidata_client.query(query, timeout=5)
        types = []
        for item in bindings:
            if "type" in item and "value" in item["type"]:
                uri = item["type"]["value"]
                types.append(uri.split("/")[-1])
        
        set_file_cache("entity_type.json", cache_key, types)
        return types
    except Exception as e:
        print(f"[WARN] Failed to get entity type for {wikidata_id}: {e}")
        return []
