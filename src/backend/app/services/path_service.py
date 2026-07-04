from typing import Optional, List, Dict, Callable
import requests
import time

from app.services.bfs_service import find_path_sync
from app.services.neighbor_wikidata import get_neighbors, get_entity_type
from app.services.file_cache import get_cache, set_cache, load_cache, save_cache
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

    # find_path_sync returns List[str]
    path_qids = find_path_sync(start_qid, target_qid, get_neighbors, max_depth)
    
    if path_qids:
        set_cache("paths.json", cache_key, path_qids)
        return resolve_labels(path_qids)
    else: 
        print(f"[PATH] No path found from {start_qid} to {target_qid}")
        
    return None


def make_heuristic_neighbor_fetcher(
    target_qid: str,
    raw_get_neighbors: Callable[[str], List[str]],
) -> Callable[[str], List[str]]:
    """
    Tạo ra một hàm get_neighbors có tích hợp logic lọc/phân cấp thực thể (Person/Hub)
    và ưu tiên hub đích (target_hubs).
    """
    target_hubs = set()
    try:
        target_nbs = raw_get_neighbors(target_qid)
        for nb in target_nbs:
            types = get_entity_type(nb)
            if any(t in ALLOWED_HUB_CLASSES for t in types):
                target_hubs.add(nb)
    except Exception as e:
        print(f"[WARN] Failed to resolve target hubs for {target_qid}: {e}")

    def heuristic_fetcher(node: str) -> List[str]:
        try:
            current_types = get_entity_type(node)
        except Exception as e:
            print(f"[WARN] Failed to get entity type for {node}: {e}")
            return []

        if "Q5" in current_types:
            current_kind = "person"
        elif any(t in ALLOWED_HUB_CLASSES for t in current_types):
            current_kind = "hub"
        else:
            return []

        try:
            raw_neighbors = raw_get_neighbors(node)
        except Exception as e:
            print(f"[WARN] Failed to get neighbors for {node}: {e}")
            return []

        priority_nbs = []
        normal_nbs = []

        for nb in raw_neighbors:
            try:
                nb_types = get_entity_type(nb)
            except Exception as e:
                print(f"[WARN] Failed to get entity type for {nb}: {e}")
                continue

            if "Q5" in nb_types:
                nb_kind = "person"
            elif any(t in ALLOWED_HUB_CLASSES for t in nb_types):
                nb_kind = "hub"
            else:
                continue

            if current_kind == "hub" and nb_kind == "hub":
                continue

            if target_hubs and current_kind == "hub" and nb in target_hubs:
                priority_nbs.insert(0, nb)
            else:
                normal_nbs.append(nb)

        return priority_nbs + normal_nbs

    return heuristic_fetcher


def find_path_bidirectional(
    start_qid: str,
    target_qid: str,
    max_depth: int = 4,
) -> Optional[List[Dict[str, str]]]:
    """
    Bidirectional BFS to find shortest path between two Wikidata QIDs.
    Returns path with labels: [{'qid': '...', 'label': '...'}, ...]
    Centralized core search logic in bfs_service.py.
    """
    if start_qid == target_qid:
        return resolve_labels([start_qid])

    heuristic_fetcher = make_heuristic_neighbor_fetcher(target_qid, get_neighbors)

    path_qids = find_path_sync(
        start=start_qid,
        target=target_qid,
        get_neighbors=heuristic_fetcher,
        max_depth=max_depth,
    )

    if path_qids:
        return resolve_labels(path_qids)
    return None
