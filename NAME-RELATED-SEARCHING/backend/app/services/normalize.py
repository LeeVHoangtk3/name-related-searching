from typing import List, Dict
import requests

WIKIDATA_SEARCH_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": (
        "WikiBFS/1.0 "
        "(https://github.com/LeeVHoangtk3/name-related-searching; "
        "contact: leviethoangtk3@gmail.com)"
    )
}

TIMEOUT = 15
DEFAULT_LIMIT = 5


def normalize_name(
    name: str,
    limit: int = DEFAULT_LIMIT,
    language: str = "en",
) -> List[Dict]:

    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": language,
        "format": "json",
        "limit": limit,
        # chỉ ưu tiên entity là người
        "type": "item",
    }

    response = requests.get(
        WIKIDATA_SEARCH_API,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Wikidata search error {response.status_code}: "
            f"{response.text[:300]}"
        )

    data = response.json()
    search_results = data.get("search", [])

    candidates: List[Dict] = []

    for item in search_results:
        # chỉ giữ entity là human nếu có description
        candidate = {
            "qid": item.get("id"),
            "label": item.get("label"),
            "description": item.get("description", ""),
            "score": item.get("score", 0.0),
        }
        candidates.append(candidate)

    return candidates


# =========================
# MANUAL TEST
# =========================

if __name__ == "__main__":
    tests = [
        "Michael Jordan",
        "Nguyễn Nhật Ánh",
        "John Smith",
    ]

    for name in tests:
        print(f"\nNormalize: {name}")
        results = normalize_name(name, limit=5, language="en")

        for c in results:
            print(
                f"- {c['qid']:8} | {c['label']} "
                f"({c['description']}) | score={c['score']}"
            )
