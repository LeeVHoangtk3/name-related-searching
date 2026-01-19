import requests
from typing import List

from app.services.file_cache import get_cache, set_cache

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "User-Agent": "name-related-searching/0.1 (contact: leviethoangtk3@gmail.com)",
    "Accept": "application/sparql-results+json",
}



def get_neighbors(qid: str) -> List[str]:
    cache_key = f"neighbors:{qid}"
    cached = get_cache("neighbors.json", cache_key, ttl=86400)
    if cached is not None:
        return cached

    query = f"""
    SELECT ?neighbor WHERE {{
      wd:{qid} ?p ?neighbor .
      ?neighbor wdt:P31 wd:Q5 .
    }}
    LIMIT 50
    """

    res = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers=HEADERS,
        timeout=20,
    )

    try:
        data = res.json()
    except Exception as e:
        print("❌ Wikidata response not JSON")
        print("Status:", res.status_code)
        print("Body:", res.text[:500])
        return []   # 🔥 QUAN TRỌNG: không crash API

    neighbors = []
    for item in data.get("results", {}).get("bindings", []):
        uri = item["neighbor"]["value"]
        neighbors.append(uri.split("/")[-1])

    set_cache("neighbors.json", cache_key, neighbors)
    return neighbors
