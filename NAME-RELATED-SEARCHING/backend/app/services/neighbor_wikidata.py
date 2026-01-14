"""
neighbor_wikidata.py

Nhiệm vụ:
- Nhận vào 1 Wikidata ID (Qxxx)
- Trả về danh sách Wikidata ID của các "neighbor" (người liên quan)

Định nghĩa neighbor (MVP):
- Entity có liên kết trực tiếp
- instance of human (P31 = Q5)

KHÔNG crawl HTML Wikipedia
CHỈ dùng Wikidata SPARQL API
"""

from typing import List
import requests

# =========================
# CONFIG
# =========================

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# ⚠️ User-Agent BẮT BUỘC phải có contact thật
HEADERS = {
    "Accept": "application/sparql+json",
    "User-Agent": (
        "WikiBFS/1.0 "
        "(https://github.com/yourname/name-related-searching; "
        "contact: your_email@gmail.com)"
    ),
}

DEFAULT_LIMIT = 50
TIMEOUT = 15  # seconds


# =========================
# SPARQL QUERY BUILDER
# =========================

def build_neighbor_query(wikidata_id: str, limit: int = DEFAULT_LIMIT) -> str:
    """
    Build SPARQL query to fetch human neighbors of a Wikidata entity.
    """
    return f"""
    SELECT ?neighbor WHERE {{
      wd:{wikidata_id} ?p ?neighbor .
      ?neighbor wdt:P31 wd:Q5 .
    }}
    LIMIT {limit}
    """


# =========================
# CORE FUNCTION
# =========================

def get_neighbors(wikidata_id: str) -> List[str]:
    """
    Get neighbor Wikidata IDs for a given Wikidata ID.

    Args:
        wikidata_id (str): e.g. "Q34660"

    Returns:
        List[str]: list of Wikidata IDs, e.g. ["Q123", "Q456"]
    """

    query = build_neighbor_query(wikidata_id)

    # DÙNG POST (ổn định hơn GET)
    response = requests.post(
        WIKIDATA_ENDPOINT,
        data={"query": query},
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    # Nếu Wikidata trả lỗi → fail sớm cho dễ debug
    if response.status_code != 200:
        raise RuntimeError(
            f"Wikidata error {response.status_code}: "
            f"{response.text[:300]}"
        )

    # Parse JSON
    data = response.json()
    bindings = data.get("results", {}).get("bindings", [])

    neighbors: List[str] = []

    for item in bindings:
        uri = item["neighbor"]["value"]
        # Ví dụ:
        # https://www.wikidata.org/entity/Q12345
        qid = uri.split("/")[-1]
        neighbors.append(qid)

    return neighbors


# =========================
# MANUAL TEST
# =========================

if __name__ == "__main__":
    # J. K. Rowling = Q34660
    test_qid = "Q34660"

    print(f"Testing neighbors for {test_qid} ...")

    result = get_neighbors(test_qid)

    print(f"Found {len(result)} neighbors")
    for q in result[:10]:
        print("-", q)
