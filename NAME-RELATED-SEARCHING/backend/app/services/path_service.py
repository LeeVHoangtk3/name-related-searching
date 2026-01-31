from typing import Optional, List, Dict
from collections import deque
import requests
import time

from app.services.bfs_service import find_path
from app.services.neighbor_wikidata import get_neighbors
from app.services.file_cache import get_cache, set_cache, load_cache, save_cache
from app.services.neighbor_wikidata import get_entity_type
from app.services.graph_config import ALLOWED_HUB_CLASSES

def resolve_labels(qids: List[str]) -> List[Dict[str, str]]:
    """
    Given a list of QIDs, return a list of dicts: {'qid': 'Q...', 'label': '...'}
    Uses local cache 'labels.json' and fetches missing ones from Wikidata.
    """
    if not qids:
        return []

    cache_file = "labels.json"
    cache = load_cache(cache_file)
    
    missing = []
    results = {}
    
    # Check cache
    for qid in qids:
        # Cache entry format: {"value": "Label", "_created_at": timestamp}
        if qid in cache and "value" in cache[qid]:
            results[qid] = cache[qid]["value"]
        else:
            missing.append(qid)

    # Batch fetch missing labels
    if missing:
        # Process in chunks of 50 (Wikidata limit)
        chunk_size = 50
        for i in range(0, len(missing), chunk_size):
            chunk = missing[i:i + chunk_size]
            ids_str = "|".join(chunk)
            
            try:
                resp = requests.get(
                    "https://www.wikidata.org/w/api.php",
                    params={
                        "action": "wbgetentities",
                        "ids": ids_str,
                        "props": "labels",
                        "languages": "en",
                        "format": "json"
                    },
                    headers={
                        "User-Agent": "name-related-searching/0.1"
                    },
                    timeout=10
                )
                
                data = resp.json()
                entities = data.get("entities", {})
                
                for qid in chunk:
                    label = qid  # Fallback to QID
                    if qid in entities:
                        # Extract English label if available
                        labels = entities[qid].get("labels", {})
                        if "en" in labels and "value" in labels["en"]:
                            label = labels["en"]["value"]
                    
                    results[qid] = label
                    # Update cache object
                    cache[qid] = {
                        "value": label,
                        "_created_at": time.time()
                    }
                    
            except Exception as e:
                print(f"❌ Error fetching labels for chunk {chunk}: {e}")
                # Fallback for failed items so we don't crash
                for qid in chunk:
                    if qid not in results:
                        results[qid] = qid

        # Save updated cache to disk once
        save_cache(cache_file, cache)

    # Reconstruct the path in original order with labels
    final_path = []
    for qid in qids:
        final_path.append({
            "qid": qid,
            "label": results.get(qid, qid)
        })
        
    return final_path


def find_path_cached(
    start_qid: str,
    target_qid: str,
    max_depth: int = 4,
) -> Optional[List[Dict[str, str]]]:

    cache_key = f"path:{start_qid}:{target_qid}"
    # Cached value is the raw QID list to save space (or we can cache full objects)
    # Let's assume we cache the raw path (list of strings) to be consistent with previous logic,
    # and resolve labels effectively. 
    # BUT wait, the previous code cached the return value of find_path (which was List[str]).
    # If I change return type, I should update cache logic.
    # To keep it robust: let's cache the LIST OF QIDS (List[str]).
    # Then resolve labels every time (but labels themselves are cached, so it's fast).
    
    cached_path_qids = get_cache("paths.json", cache_key, ttl=7 * 86400)
    
    if cached_path_qids is not None:
        # It might be the old format (List[str]) which is what we expect
        return resolve_labels(cached_path_qids)

    # find_path returns List[str]
    path_qids = find_path(start_qid, target_qid, get_neighbors, max_depth)
    
    if path_qids:
        set_cache("paths.json", cache_key, path_qids)
        return resolve_labels(path_qids)
    else: 
        print(f"[PATH] No path found from {start_qid} to {target_qid}")
        
    return None


def find_path_bidirectional(
    start_qid: str,
    target_qid: str,
    max_depth: int = 4,
) -> Optional[List[Dict[str, str]]]:
    """
    Bidirectional BFS to find shortest path between two Wikidata QIDs.
    Returns path with labels: [{'qid': '...', 'label': '...'}, ...]
    """

    if start_qid == target_qid:
        return resolve_labels([start_qid])

    # Queues
    q_start = deque([start_qid])
    q_target = deque([target_qid])

    # Visited sets (store QIDs)
    visited_start = {start_qid: "person"}
    visited_target = {target_qid: "person"} 

    # Parent maps
    parent_start = {start_qid: None}
    parent_target = {target_qid: None}


    while q_start and q_target:

        # Expand the smaller frontier
        if len(q_start) <= len(q_target):
            meet = _expand(
                q_start,
                visited_start,
                visited_target,
                parent_start,
            )
        else:
            meet = _expand(
                q_target,
                visited_target,
                visited_start,
                parent_target,
            )

        if meet:
            path_qids = _build_path(meet, parent_start, parent_target)
            return resolve_labels(path_qids)

    return None


def _expand(queue, visited_this, visited_other, parent):
    """
    Expand one BFS layer with graph control:
    - Person → Hub → Person
    - ❌ Hub → Hub (blocked)
    """
    for _ in range(len(queue)):
        current = queue.popleft()
        current_kind = visited_this[current]   # "person" | "hub"

        neighbors = get_neighbors(current)

        for nb in neighbors:
            if nb in visited_this:
                continue

            # xác định loại của neighbor
            types = get_entity_type(nb)
            nb_kind = (
                "person" if "Q5" in types
                else "hub" if any(t in ALLOWED_HUB_CLASSES for t in types)
                else None
            )

            # bỏ qua node không hợp lệ
            if nb_kind is None:
                continue

            # 🚫 chặn HUB → HUB
            if current_kind == "hub" and nb_kind == "hub":
                continue

            parent[nb] = current
            visited_this[nb] = nb_kind

            # 🤝 gặp nhau
            if nb in visited_other:
                return nb

            queue.append(nb)

    return None



def _build_path(meet, parent_start, parent_target):
    """
    Reconstruct path from both sides.
    Returns List[str] (QIDs)
    """
    path_start = []
    cur = meet
    while cur:
        path_start.append(cur)
        cur = parent_start.get(cur)
    path_start.reverse()

    path_target = []
    cur = parent_target.get(meet)
    while cur:
        path_target.append(cur)
        cur = parent_target.get(cur)

    return path_start + path_target
