import asyncio
import json
import logging
from collections import Counter
from app.clients.wikidata import wikidata_client
from app.services.neighbor_wikidata import build_neighbor_query
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

STRATEGIC_HUBS = ["Q5", "Q30", "Q571", "Q11424", "Q4830453"]
SYNC_INTERVAL_SECONDS = 3600  # 1 hour
HUB_CACHE_TTL_SECONDS = 24 * 3600  # 24 hours
PREFETCH_LIMIT = 500

def get_dynamic_hubs_from_history(limit: int = 5) -> list:
    """
    Quét lịch sử tìm kiếm từ Redis, đếm tần suất xuất hiện của các QID
    và trả về danh sách các QID xuất hiện nhiều nhất (Dynamic Hubs).
    """
    try:
        records = redis_client.lrange("global_history", 0, -1)
        if not records:
            return []
        
        qids = []
        for record in records:
            try:
                data = json.loads(record)
                if "start" in data:
                    qids.append(data["start"])
                if "target" in data:
                    qids.append(data["target"])
            except Exception:
                continue
        
        if not qids:
            return []
        
        counter = Counter(qids)
        top_hubs = [qid for qid, _ in counter.most_common(limit)]
        return top_hubs
    except Exception as e:
        logger.warning(f"[WARN] Failed to extract dynamic hubs from history: {e}")
        return []

async def prefetch_hub_neighbors(hub_qid: str):
    """
    Thực hiện tải trước danh sách láng giềng của Hub qua SPARQL query sử dụng asyncio.to_thread.
    Pre-fetch neighbors for a Hub via SPARQL using asyncio.to_thread.
    """
    logger.info(f"[INFO] Pre-fetching neighbors for Hub {hub_qid}...")
    query = build_neighbor_query(hub_qid, limit=PREFETCH_LIMIT)
    try:
        # Run Wikidata query in a separate thread to keep Event Loop non-blocking
        bindings = await asyncio.to_thread(wikidata_client.query, query, timeout=30)
        neighbors = []
        for item in bindings:
            if "neighbor" in item and "value" in item["neighbor"]:
                uri = item["neighbor"]["value"]
                neighbors.append(uri.split("/")[-1])
        
        cache_key = f"hub_cache:{hub_qid}"
        try:
            redis_client.set(cache_key, json.dumps(neighbors), ex=HUB_CACHE_TTL_SECONDS)
            logger.info(f"[INFO] Successfully cached {len(neighbors)} neighbors for Hub {hub_qid}")
        except Exception as e:
            logger.warning(f"[WARN] Failed to write Hub {hub_qid} to Redis cache: {e}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to query neighbors for Hub {hub_qid}: {e}")

async def sync_hubs_cache_worker():
    """
    Worker chạy nền tự động đồng bộ cache định kỳ mỗi 1 tiếng.
    Quét lịch sử tìm kiếm để phát hiện Dynamic Hubs bổ sung vào danh sách pre-fetch.
    """
    logger.info("[INFO] Hubs cache syncer worker started.")
    while True:
        logger.info("[INFO] Starting Hubs Cache pre-fetch...")
        
        # Kết hợp Strategic Hubs cố định và Dynamic Hubs từ lịch sử
        hubs_to_sync = list(STRATEGIC_HUBS)
        dynamic_hubs = get_dynamic_hubs_from_history(limit=5)
        
        for dh in dynamic_hubs:
            if dh not in hubs_to_sync:
                hubs_to_sync.append(dh)
                
        logger.info(f"[INFO] Dynamic and Strategic Hubs to sync: {hubs_to_sync}")
        for hub_qid in hubs_to_sync:
            await prefetch_hub_neighbors(hub_qid)
        
        logger.info(f"[INFO] Hubs Cache pre-fetch completed. Sleeping for {SYNC_INTERVAL_SECONDS} seconds...")
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)

_syncer_task = None

async def start_cache_syncer_task():
    global _syncer_task
    if _syncer_task is None:
        _syncer_task = asyncio.create_task(sync_hubs_cache_worker())
        logger.info("[INFO] Cache syncer background task launched.")

async def stop_cache_syncer_task():
    global _syncer_task
    if _syncer_task is not None:
        _syncer_task.cancel()
        try:
            await _syncer_task
        except asyncio.CancelledError:
            logger.info("[INFO] Cache syncer background task cancelled.")
        _syncer_task = None
