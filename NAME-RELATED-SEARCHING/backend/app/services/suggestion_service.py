from typing import Any, Dict, List, Optional

from app.clients.wikidata import wikidata_client
from app.core.redis import get_history


def collect_history_qids(history: List[Dict[str, str]]) -> List[str]:
    qids: List[str] = []
    seen = set()
    for record in history:
        for field in ("start", "target"):
            qid = str(record.get(field, "")).strip().upper()
            if not qid or qid in seen:
                continue
            seen.add(qid)
            qids.append(qid)
    return qids


def build_history_suggestions(
    history: List[Dict[str, str]],
    query: str,
    limit: int,
    entity_summaries: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    entity_summaries = entity_summaries or {}
    items: List[Dict[str, str]] = []
    seen = set()
    for record in history:
        for field in ("start", "target"):
            qid = str(record.get(field, "")).strip().upper()
            if not qid or qid in seen:
                continue
            entity = entity_summaries.get(qid, {})
            label = str(entity.get("label") or qid).strip() or qid
            description = str(entity.get("description") or "").strip()
            searchable_text = " ".join(part for part in (qid, label, description) if part).lower()
            if query_lower not in searchable_text:
                continue
            seen.add(qid)
            items.append(
                {
                    "qid": qid,
                    "label": label,
                    "description": description or "From search history",
                    "source": "history",
                }
            )
            if len(items) >= limit:
                return items
    return items


def merge_suggestions(
    wikidata_items: List[Dict[str, str]], history_items: List[Dict[str, str]], limit: int
) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    seen = set()
    for source_items in (wikidata_items, history_items):
        for item in source_items:
            qid = str(item.get("qid", "")).strip()
            if not qid or qid in seen:
                continue
            seen.add(qid)
            merged.append(item)
            if len(merged) >= limit:
                return merged
    return merged


def get_name_suggestions(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    try:
        history = get_history()
    except Exception:
        history = []

    history_qids = collect_history_qids(history)
    try:
        entity_summaries = wikidata_client.get_entity_summaries(history_qids)
    except Exception:
        entity_summaries = {}

    history_items = build_history_suggestions(
        history,
        normalized_query,
        limit,
        entity_summaries=entity_summaries,
    )

    try:
        wikidata_items = wikidata_client.search_entities(normalized_query, limit=limit)
    except Exception:
        wikidata_items = []

    return merge_suggestions(wikidata_items, history_items, limit)
