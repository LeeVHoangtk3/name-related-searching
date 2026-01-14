from typing import List
import requests

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "User-Agent": (
        "WikiBFS/1.0 "
        "(https://github.com/LeeVHoangtk3/name-related-searching; "
        "contact: leviethoangtk3@gmail.com)"
    ),
}

TIMEOUT = 20
DEFAULT_LIMIT = 50


def build_neighbor_query(wikidata_id: str, limit: int = DEFAULT_LIMIT) -> str:
    return f"""
    SELECT ?neighbor WHERE {{
      wd:{wikidata_id} ?p ?neighbor .
      ?neighbor wdt:P31 wd:Q5 .
    }}
    LIMIT {limit}
    """


def get_neighbors(wikidata_id: str) -> List[str]:
    query = build_neighbor_query(wikidata_id)

    response = requests.post(
        WIKIDATA_ENDPOINT,
        data={
            "query": query,
            "format": "json",
        },
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Wikidata HTTP {response.status_code}\n"
            f"{response.text[:300]}"
        )

    # ✅ FIX: chấp nhận sparql-results+json
    content_type = response.headers.get("Content-Type", "")
    if "+json" not in content_type:
        raise RuntimeError(
            "Wikidata did NOT return JSON!\n"
            f"Content-Type: {content_type}\n"
            f"Body:\n{response.text[:300]}"
        )

    data = response.json()
    bindings = data["results"]["bindings"]

    neighbors: List[str] = []
    for item in bindings:
        uri = item["neighbor"]["value"]
        neighbors.append(uri.split("/")[-1])

    return neighbors


# =========================
# MANUAL TEST
# =========================

# if __name__ == "__main__":
#     print("Testing neighbors for Q34660 (J. K. Rowling)")
#     result = get_neighbors("Q34660")

#     print(f"Found {len(result)} neighbors")
#     for q in result[:10]:
#         print("-", q)
