import requests
from typing import List, Dict, Any

from app.services.file_cache import get_cache, set_cache
from app.services.input_utils import normalize_input
from app.clients.wikidata import wikidata_client

WIKIDATA_SEARCH_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "name-related-searching/0.1 (contact: leviethoangtk3@gmail.com)",
    "Accept": "application/json",
}

def normalize_name(name: str, limit: int = 5) -> List[Dict]:
    normalized = normalize_input(name)
    cache_key = f"normalize:{normalized}"

    cached = get_cache("normalize.json", cache_key, ttl=7 * 86400)
    if cached is not None:
        return cached

    params = {
        "action": "wbsearchentities",
        "search": normalized,
        "language": "en",
        "format": "json",
        "limit": limit,
    }

    res = requests.get(
        WIKIDATA_SEARCH_API,
        params=params,
        headers=HEADERS,
        timeout=15,
    )

    # ❗ Không để crash API
    try:
        res.raise_for_status()
        data = res.json()
    except Exception:
        print("❌ Wikidata search failed")
        print("Status:", res.status_code)
        print("Body:", res.text[:500])
        return []

    results = []
    for item in data.get("search", []):
        results.append({
            "qid": item.get("id"),
            "label": item.get("label"),
            "description": item.get("description", ""),
            "score": item.get("score", 0),
        })

    set_cache("normalize.json", cache_key, results)
    return results


def normalize_graph_payload(raw_bindings: List[Dict]) -> List[Dict]:
    """
    Chuẩn hóa các raw SPARQL bindings để trả về payload đồ thị gọn nhẹ,
    chỉ giữ lại strictly 'id', 'name', và 'p_label'.
    """
    normalized = []
    for binding in raw_bindings:
        node_id = binding.get("neighbor", {}).get("value", "").split("/")[-1]
        node_name = binding.get("neighborLabel", {}).get("value", "") or node_id
        
        p_url = binding.get("p", {}).get("value", "")
        p_id = p_url.split("/")[-1] if p_url else ""
        p_label = binding.get("pLabel", {}).get("value", "") or p_id
        
        normalized.append({
            "id": node_id,
            "name": node_name,
            "p_label": p_label
        })
    return normalized


def get_edge_properties(path: List[str]) -> Dict[str, str]:
    """
    Lấy nhãn thuộc tính (property labels) kết nối giữa các node kề nhau trên path.
    Trả về dictionary với key là "source_qid->target_qid" và value là "p_label".
    """
    if len(path) < 2:
        return {}
    
    # Xây dựng các cặp kề nhau
    pairs = []
    for i in range(len(path) - 1):
        s = path[i]
        t = path[i+1]
        pairs.append(f"(wd:{s} wd:{t})")
        pairs.append(f"(wd:{t} wd:{s})")
    
    pairs_str = " ".join(pairs)
    query = f"""
    SELECT DISTINCT ?source ?target ?pLabel WHERE {{
      VALUES (?source ?target) {{ {pairs_str} }}
      ?source ?p ?target .
      ?property wikibase:directClaim ?p .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    edge_labels = {}
    try:
        bindings = wikidata_client.query(query, timeout=8)
        for item in bindings:
            src_uri = item.get("source", {}).get("value", "")
            tgt_uri = item.get("target", {}).get("value", "")
            p_label = item.get("pLabel", {}).get("value", "")
            
            if src_uri and tgt_uri and p_label:
                src_qid = src_uri.split("/")[-1]
                tgt_qid = tgt_uri.split("/")[-1]
                # Lưu cả hai chiều để dễ tra cứu
                edge_labels[f"{src_qid}->{tgt_qid}"] = p_label
                edge_labels[f"{tgt_qid}->{src_qid}"] = p_label
    except Exception as e:
        print(f"[WARN] Failed to get edge property labels: {e}")
        
    return edge_labels


def minimize_graph_payload(path: List[str]) -> Dict[str, Any]:
    """
    Tiếp nhận danh sách QID trên path, phân giải nhãn thực thể và thuộc tính kết nối,
    trả về cấu trúc đồ thị phẳng cực kỳ tối giản (nodes: id/name, links: source/target/p_label).
    """
    if not path:
        return {"nodes": [], "links": []}
    
    # 1. Phân giải nhãn cho các QID thực thể
    summaries = {}
    try:
        summaries = wikidata_client.get_entity_summaries(path)
    except Exception as e:
        print(f"[WARN] Failed to get entity summaries: {e}")
    
    nodes = []
    for qid in path:
        name = summaries.get(qid, {}).get("label") or qid
        nodes.append({
            "id": qid,
            "name": name
        })
    
    # 2. Phân giải nhãn thuộc tính cho các cạnh
    edge_labels = get_edge_properties(path)
    
    links = []
    for i in range(len(path) - 1):
        s = path[i]
        t = path[i+1]
        p_label = edge_labels.get(f"{s}->{t}") or edge_labels.get(f"{t}->{s}") or "connected to"
        links.append({
            "source": s,
            "target": t,
            "p_label": p_label
        })
        
    return {"nodes": nodes, "links": links}
