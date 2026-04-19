import requests
from typing import List, Dict, Any
from app.core.config import settings

class WikidataClient:
    """
    Client chuyên dụng để tương tác với Wikidata SPARQL API.
    Dedicated client to interact with Wikidata SPARQL API.
    """
    
    def __init__(self):
        self.endpoint = settings.WIKIDATA_ENDPOINT
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/sparql-results+json"
        }
        self.timeout = settings.TIMEOUT

    def query(self, sparql: str) -> List[Dict[str, Any]]:
        """
        Thực hiện truy vấn SPARQL đến Wikidata.
        Execute a SPARQL query to Wikidata.
        """
        response = requests.post(
            self.endpoint,
            data={"query": sparql, "format": "json"},
            headers=self.headers,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"Wikidata API error: {response.status_code} - {response.text[:200]}")
            
        data = response.json()
        return data.get("results", {}).get("bindings", [])

wikidata_client = WikidataClient()
