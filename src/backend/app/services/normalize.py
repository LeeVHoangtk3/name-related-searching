import requests
from typing import List, Dict, Any

from app.services.file_cache import get_cache, set_cache
from app.services.input_utils import normalize_input
from app.clients.wikidata import wikidata_client
from app.services.graph_config import INVERSE_PROPERTIES

WIKIDATA_SEARCH_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "name-related-searching/0.1 (contact: leviethoangtk3@gmail.com)",
    "Accept": "application/json",
}

# Fallback nhãn tiếng Anh của các thuộc tính phổ biến
# Fallback English labels for common properties
PROPERTY_LABELS_FALLBACK = {
    "P22": "father",
    "P25": "mother",
    "P40": "child",
    "P26": "spouse",
    "P3373": "sibling",
    "P106": "occupation",
    "P19": "place of birth",
    "P27": "country of citizenship",
    "P108": "employer",
    "P39": "office held",
    "P69": "educated at",
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

    try:
        res.raise_for_status()
        data = res.json()
    except Exception:
        print("❌ Wikidata search failed")
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


def get_edge_properties(path: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Lấy thông tin quan hệ giữa các node kề nhau trên path (bao gồm cả property ID và label).
    Trả về dictionary với key là "source_qid->target_qid" và value là {"p_id": "P...", "p_label": "..."}.
    """
    if len(path) < 2:
        return {}
    
    pairs = []
    for i in range(len(path) - 1):
        s = path[i]
        t = path[i+1]
        pairs.append(f"(wd:{s} wd:{t})")
        pairs.append(f"(wd:{t} wd:{s})")
    
    pairs_str = " ".join(pairs)
    query = f"""
    SELECT DISTINCT ?source ?target ?property ?pLabel WHERE {{
      VALUES (?source ?target) {{ {pairs_str} }}
      ?source ?p ?target .
      ?property wikibase:directClaim ?p .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    edge_data = {}
    try:
        bindings = wikidata_client.query(query, timeout=8)
        for item in bindings:
            src_uri = item.get("source", {}).get("value", "")
            tgt_uri = item.get("target", {}).get("value", "")
            prop_uri = item.get("property", {}).get("value", "")
            p_label = item.get("pLabel", {}).get("value", "")
            
            if src_uri and tgt_uri and prop_uri:
                src_qid = src_uri.split("/")[-1]
                tgt_qid = tgt_uri.split("/")[-1]
                p_id = prop_uri.split("/")[-1]
                
                edge_data[f"{src_qid}->{tgt_qid}"] = {
                    "p_id": p_id,
                    "p_label": p_label
                }
    except Exception as e:
        print(f"[WARN] Failed to get edge property labels: {e}")
        
    return edge_data


def minimize_graph_payload(path: List[str]) -> Dict[str, Any]:
    """
    Tiếp nhận danh sách QID trên path, phân giải nhãn thực thể và thuộc tính kết nối,
    trả về cấu trúc đồ thị phẳng cực kỳ tối giản (nodes: id/name, links: source/target/p_label).
    Có xử lý thuộc tính nghịch đảo cho đường đi ngược.
    """
    if not path:
        return {"nodes": [], "links": []}
    
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
    
    edge_data = get_edge_properties(path)
    links = []
    
    for i in range(len(path) - 1):
        s = path[i]
        t = path[i+1]
        
        p_label = "connected to"
        
        # 1. Kiểm tra xem có quan hệ xuôi s -> t không
        if f"{s}->{t}" in edge_data:
            p_label = edge_data[f"{s}->{t}"]["p_label"]
        # 2. Nếu không có quan hệ xuôi, kiểm tra quan hệ ngược t -> s
        elif f"{t}->{s}" in edge_data:
            reverse_relation = edge_data[f"{t}->{s}"]
            p_id = reverse_relation["p_id"]
            
            # Nếu thuộc tính ngược nằm trong INVERSE_PROPERTIES, hoán đổi thuộc tính
            if p_id in INVERSE_PROPERTIES:
                inv_p_id = INVERSE_PROPERTIES[p_id]
                # Lấy nhãn của thuộc tính nghịch đảo
                p_label = PROPERTY_LABELS_FALLBACK.get(inv_p_id) or inv_p_id
            else:
                p_label = f"inverse of {reverse_relation['p_label']}"
        
        links.append({
            "source": s,
            "target": t,
            "p_label": p_label
        })
        
    return {"nodes": nodes, "links": links}
