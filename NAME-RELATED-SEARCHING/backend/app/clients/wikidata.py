import requests
from typing import List, Dict, Any, Optional
from app.core.config import settings

class WikidataClient:
    """
    Client chuyên dụng để tương tác với Wikidata SPARQL API.
    Dedicated client to interact with Wikidata SPARQL API.
    """
    
    def __init__(self):
        self.endpoint = settings.WIKIDATA_ENDPOINT
        self.search_endpoint = "https://www.wikidata.org/w/api.php"
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/sparql-results+json"
        }
        self.timeout = settings.TIMEOUT

    def query(self, sparql: str, timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Thực hiện truy vấn SPARQL đến Wikidata.
        Execute a SPARQL query to Wikidata.
        """
        effective_timeout = self.timeout if timeout is None else timeout
        response = requests.post(
            self.endpoint,
            data={"query": sparql, "format": "json"},
            headers=self.headers,
            timeout=effective_timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"Wikidata API error: {response.status_code} - {response.text[:200]}")
            
        data = response.json()
        return data.get("results", {}).get("bindings", [])

    def search_entities(self, query: str, limit: int = 8, language: str = "en") -> List[Dict[str, Any]]:
        """
        Tìm kiếm thực thể Wikidata theo tên bằng wbsearchentities.
        Search Wikidata entities by name using wbsearchentities.
        """
        response = requests.get(
            self.search_endpoint,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": language,
                "format": "json",
                "limit": limit,
                "type": "item",
            },
            headers={"User-Agent": settings.USER_AGENT},
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Wikidata Search API error: {response.status_code} - {response.text[:200]}")

        data = response.json()
        items: List[Dict[str, Any]] = []
        for raw in data.get("search", []):
            qid = raw.get("id")
            if not qid:
                continue
            items.append(
                {
                    "qid": qid,
                    "label": raw.get("label") or qid,
                    "description": raw.get("description", ""),
                    "source": "wikidata",
                }
            )
        return items

    def get_entity_summaries(self, qids: List[str], language: str = "en") -> Dict[str, Dict[str, str]]:
        """
        Lấy nhãn và mô tả cho danh sách QID bằng wbgetentities.
        Fetch labels and descriptions for a list of QIDs using wbgetentities.
        """
        normalized_qids: List[str] = []
        seen = set()
        for raw_qid in qids:
            qid = str(raw_qid).strip().upper()
            if not qid or qid in seen:
                continue
            seen.add(qid)
            normalized_qids.append(qid)

        if not normalized_qids:
            return {}

        response = requests.get(
            self.search_endpoint,
            params={
                "action": "wbgetentities",
                "ids": "|".join(normalized_qids),
                "languages": language,
                "props": "labels|descriptions",
                "format": "json",
            },
            headers={"User-Agent": settings.USER_AGENT},
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Wikidata Entity API error: {response.status_code} - {response.text[:200]}")

        data = response.json()
        entities = data.get("entities", {})
        summaries: Dict[str, Dict[str, str]] = {}
        for qid in normalized_qids:
            entity = entities.get(qid, {})
            label = entity.get("labels", {}).get(language, {}).get("value") or qid
            description = entity.get("descriptions", {}).get(language, {}).get("value", "")
            summaries[qid] = {"label": label, "description": description}
        return summaries

wikidata_client = WikidataClient()
