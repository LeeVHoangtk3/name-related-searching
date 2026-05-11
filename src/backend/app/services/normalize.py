import requests
from typing import List, Dict

from app.services.file_cache import get_cache, set_cache
from app.services.input_utils import normalize_input

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
    except Exception as e:
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
