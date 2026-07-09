from typing import Optional, List, Dict, Callable
import requests
import time
import threading

from app.services.bfs_service import find_path_sync
from app.services.neighbor_wikidata import get_neighbors, get_entity_type
from app.services.file_cache import get_cache, set_cache, load_cache, save_cache
from app.services.graph_config import ALLOWED_HUB_CLASSES
from app.core.graph_db import get_db_session

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
        if qid in cache and "value" in cache[qid]:
            results[qid] = cache[qid]["value"]
        else:
            missing.append(qid)

    # Batch fetch missing labels
    if missing:
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
                    label = qid
                    if qid in entities:
                        labels = entities[qid].get("labels", {})
                        if "en" in labels and "value" in labels["en"]:
                            label = labels["en"]["value"]
                    
                    results[qid] = label
                    cache[qid] = {
                        "value": label,
                        "_created_at": time.time()
                    }
                    
            except Exception as e:
                print(f"❌ Error fetching labels for chunk {chunk}: {e}")
                for qid in chunk:
                    if qid not in results:
                        results[qid] = qid

        save_cache(cache_file, cache)

    final_path = []
    for qid in qids:
        final_path.append({
            "qid": qid,
            "label": results.get(qid, qid)
        })
        
    return final_path


# --- Memgraph DB Integrations ---

def find_path_in_memgraph(start_id: str, target_id: str, max_depth: int) -> Optional[List[str]]:
    """
    Tìm kiếm đường đi ngắn nhất giữa hai QID bằng câu lệnh Cypher shortestPath trong Memgraph DB.
    """
    session = get_db_session()
    if session is None:
        return None
    try:
        with session:
            # Query shortestPath using undirected relationships
            result = session.run(
                f"""
                MATCH p = shortestPath((start:Entity {{id: $start_id}})-[*..{max_depth}]-(target:Entity {{id: $target_id}}))
                RETURN p
                """,
                start_id=start_id, target_id=target_id
            )
            record = result.single()
            if record:
                neo_path = record["p"]
                node_ids = [node["id"] for node in neo_path.nodes]
                return node_ids
    except Exception as e:
        print(f"[WARN] Memgraph shortestPath query failed: {e}")
    return None


def is_path_stale(node_ids: List[str]) -> bool:
    """
    Kiểm tra xem bất kỳ nút nào trên đường đi có thời gian cập nhật 'updated_at' quá 7 ngày hay không.
    """
    session = get_db_session()
    if session is None:
        return True
    try:
        current_time_ms = int(time.time() * 1000)
        seven_days_ms = 7 * 24 * 3600 * 1000
        with session:
            result = session.run(
                """
                MATCH (n:Entity) WHERE n.id IN $node_ids
                RETURN n.id AS id, n.updated_at AS updated_at
                """,
                node_ids=node_ids
            )
            for record in result:
                updated_at = record.get("updated_at")
                if updated_at is None or (current_time_ms - updated_at > seven_days_ms):
                    return True
            return False
    except Exception:
        return True


def write_path_to_memgraph(path_qids: List[str]):
    """
    Ghi ngược (Write-back) đường đi phẳng cùng các nhãn cạnh tương ứng vào Memgraph DB dưới nền.
    """
    session = get_db_session()
    if session is None:
        return
    try:
        # Resolve names and edges properties
        resolved = resolve_labels(path_qids)
        name_map = {item["qid"]: item["label"] for item in resolved}
        
        # Import normalize internally to avoid circular dependencies
        from app.services.normalize import get_edge_properties
        edge_properties = get_edge_properties(path_qids)
        
        with session:
            current_time_ms = int(time.time() * 1000)
            for i in range(len(path_qids) - 1):
                u = path_qids[i]
                v = path_qids[i+1]
                u_name = name_map.get(u, u)
                v_name = name_map.get(v, v)
                
                p_label = "connected to"
                if f"{u}->{v}" in edge_properties:
                    p_label = edge_properties[f"{u}->{v}"]["p_label"]
                elif f"{v}->{u}" in edge_properties:
                    p_label = edge_properties[f"{v}->{u}"]["p_label"]
                
                session.run(
                    """
                    MERGE (a:Entity {id: $u_id})
                    ON CREATE SET a.name = $u_name, a.updated_at = $timestamp
                    ON MATCH SET a.updated_at = $timestamp
                    
                    MERGE (b:Entity {id: $v_id})
                    ON CREATE SET b.name = $v_name, b.updated_at = $timestamp
                    ON MATCH SET b.updated_at = $timestamp
                    
                    MERGE (a)-[r:RELATED {label: $p_label}]->(b)
                    SET r.updated_at = $timestamp
                    """,
                    u_id=u, u_name=u_name,
                    v_id=v, v_name=v_name,
                    p_label=p_label,
                    timestamp=current_time_ms
                )
    except Exception as e:
        print(f"[WARN] Failed to write path to Memgraph: {e}")


def trigger_lazy_refresh(start_qid: str, target_qid: str, max_depth: int):
    """
    Kích hoạt tiến trình cập nhật dữ liệu ngầm từ Wikidata về Memgraph (Lazy Refresh).
    """
    def refresh_task():
        try:
            print(f"[INFO] Background lazy refreshing path from {start_qid} to {target_qid}...")
            path_qids = find_path_sync(
                start=start_qid,
                target=target_qid,
                get_neighbors=get_neighbors,
                max_depth=max_depth
            )
            if path_qids:
                write_path_to_memgraph(path_qids)
                print(f"[INFO] Background lazy refresh complete for {start_qid} -> {target_qid}")
        except Exception as e:
            print(f"[WARN] Background lazy refresh failed: {e}")

    threading.Thread(target=refresh_task, daemon=True).start()


# --- Main Path Finding API Interfaces ---

def find_path_cached(
    start_qid: str,
    target_qid: str,
    max_depth: int = 4,
) -> Optional[List[Dict[str, str]]]:
    cache_key = f"path:{start_qid}:{target_qid}"
    cached_path_qids = get_cache("paths.json", cache_key, ttl=7 * 86400)
    
    if cached_path_qids is not None:
        return resolve_labels(cached_path_qids)

    # Trích xuất đường đi từ Memgraph trước
    path_qids = find_path_in_memgraph(start_qid, target_qid, max_depth)
    if path_qids:
        # Nếu trúng cache Memgraph, kiểm tra tuổi thọ
        if is_path_stale(path_qids):
            trigger_lazy_refresh(start_qid, target_qid, max_depth)
        set_cache("paths.json", cache_key, path_qids)
        return resolve_labels(path_qids)

    # Fallback chạy A* trên Wikidata
    path_qids = find_path_sync(start_qid, target_qid, get_neighbors, max_depth)
    if path_qids:
        set_cache("paths.json", cache_key, path_qids)
        # Ghi ngược vào Memgraph dưới nền
        threading.Thread(target=write_path_to_memgraph, args=(path_qids,), daemon=True).start()
        return resolve_labels(path_qids)
        
    return None


def make_heuristic_neighbor_fetcher(
    target_qid: str,
    raw_get_neighbors: Callable[[str], List[str]],
) -> Callable[[str], List[str]]:
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
    if start_qid == target_qid:
        return resolve_labels([start_qid])

    # 1. Trích xuất từ Memgraph trước
    path_qids = find_path_in_memgraph(start_qid, target_qid, max_depth)
    if path_qids:
        if is_path_stale(path_qids):
            trigger_lazy_refresh(start_qid, target_qid, max_depth)
        return resolve_labels(path_qids)

    # 2. Fallback tìm kiếm bằng thuật toán định hướng A*
    heuristic_fetcher = make_heuristic_neighbor_fetcher(target_qid, get_neighbors)
    path_qids = find_path_sync(
        start=start_qid,
        target=target_qid,
        get_neighbors=heuristic_fetcher,
        max_depth=max_depth,
    )

    if path_qids:
        # Ghi ngược vào Memgraph dưới nền
        threading.Thread(target=write_path_to_memgraph, args=(path_qids,), daemon=True).start()
        return resolve_labels(path_qids)
    return None
