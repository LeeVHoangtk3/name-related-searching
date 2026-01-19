from typing import Optional, List

from app.services.bfs_service import find_path
from app.services.neighbor_wikidata import get_neighbors
from app.services.file_cache import get_cache, set_cache


def find_path_cached(
    start_qid: str,
    target_qid: str,
    max_depth: int = 3,
) -> Optional[List[str]]:

    cache_key = f"path:{start_qid}:{target_qid}"
    cached = get_cache("paths.json", cache_key, ttl=7 * 86400)
    if cached is not None:
        return cached

    path = find_path(start_qid, target_qid, get_neighbors, max_depth)
    set_cache("paths.json", cache_key, path)
    return path
