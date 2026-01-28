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

    types = get_entity_type(qid)
    is_person = "Q5" in types
    is_org  = (
        "Q43229" in types
        or "Q783794" in types
        or any(is_subclass_of(t, "Q43229") for t in types)
    )
    is_position = "Q4164871" in types or any(is_subclass_of(t, "Q4164871") for t in types)

    if is_person:
        # Person -> Person
        query = f"""
        SELECT DISTINCT ?neighbor WHERE {{
            wd:{qid} ?p ?neighbor .
            ?neighbor wdt:P31 ?type .
            FILTER (?type IN (
                wd:Q5,
                wd:Q43229,
                wd:Q783794,
                wd:Q4164871
            ))
        }}
        LIMIT 50
        """
    elif is_org or is_position:
        # Organization/Position -> Person
        query = f"""
        SELECT DISTINCT ?neighbor WHERE {{
            ?neighbor wdt:P108|wdt:P463|wdt:P102|wdt:P39 wd:{qid} .
            ?neighbor wdt:P31 wd:Q5 .
        }}
        LIMIT 50
        """
    else: 
        return []

    res = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers=HEADERS,
        timeout=20,
    )

    try:
        res.raise_for_status()
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

def get_entity_type(qid: str) -> List[str]:
    cache_key = f"entity_type:{qid}"
    cached = get_cache("entity_type.json", cache_key, ttl=86400)
    if cached is not None:
        return cached
    
    query = f"""
    SELECT ?type WHERE {{
      wd:{qid} wdt:P31 ?type .
    }}
    LIMIT 10
    """
    res = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers=HEADERS,
        timeout=20,
    )
    try: 
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print("❌ Wikidata response not JSON")
        print("Status:", res.status_code)
        print("Body:", res.text[:500])
        return []   # 🔥 QUAN TRỌNG: không crash API
    
    types = [] 
    for item in data.get("results", {}).get("bindings", []):
        uri = item["type"]["value"]
        types.append(uri.split("/")[-1])

    set_cache("entity_type.json", cache_key, types)
    return types

def is_subclass_of(qid: str, target_qid: str) -> bool:
    cache_key = f"subclass:{qid}:{target_qid}"
    cached = get_cache("subclass.json", cache_key, ttl=86400)
    if cached is not None:
        return cached

    query = f"""
    ASK {{
      wd:{qid} wdt:P279/wdt:P279? wd:{target_qid} .
    }}
    """

    res = requests.post(
        SPARQL_ENDPOINT,
        data={"query": query},
        headers=HEADERS,
        timeout=20,
    )

    try:
        res.raise_for_status()
        data = res.json()
        result = data.get("boolean", False)
    except Exception:
        result = False

    set_cache("subclass.json", cache_key, result)
    return result

