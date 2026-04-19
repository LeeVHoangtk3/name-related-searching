from typing import List
from app.clients.wikidata import wikidata_client
from app.core.config import settings
from app.core.redis import get_cache, set_cache

def build_neighbor_query(wikidata_id: str, limit: int = settings.DEFAULT_LIMIT) -> str:
    """
    Xây dựng câu truy vấn SPARQL để tìm các thực thể lân cận (người).
    Build SPARQL query to find neighbor entities (humans).
    """
    return f"""
    SELECT ?neighbor WHERE {{
      wd:{wikidata_id} ?p ?neighbor .
      ?neighbor wdt:P31 wd:Q5 .
    }}
    LIMIT {limit}
    """

def get_neighbors(wikidata_id: str) -> List[str]:
    """
    Lấy danh sách ID của các thực thể lân cận từ Wikidata, có sử dụng Redis cache.
    Get a list of IDs of neighbor entities from Wikidata, using Redis cache.
    """
    cache_key = f"neighbors:{wikidata_id}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    query = build_neighbor_query(wikidata_id)
    bindings = wikidata_client.query(query)

    neighbors: List[str] = []
    for item in bindings:
        if "neighbor" in item and "value" in item["neighbor"]:
            uri = item["neighbor"]["value"]
            neighbors.append(uri.split("/")[-1])

    # Lưu vào cache trong 48 giờ
    # Save to cache for 48 hours
    set_cache(cache_key, neighbors, expire=172800)
    
    return neighbors
