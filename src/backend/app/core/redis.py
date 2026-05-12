import redis
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Kết nối đến Redis
# Connect to Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# In-memory fallbacks
_memory_cache = {}
_memory_history = []

def get_cache(key: str):
    """
    Lấy dữ liệu từ cache Redis.
    Get data from Redis cache.
    """
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except redis.exceptions.ConnectionError:
        return _memory_cache.get(key)

def set_cache(key: str, value: any, expire: int = 86400):
    """
    Lưu dữ liệu vào cache Redis với thời gian hết hạn (mặc định 24h).
    Save data to Redis cache with expiration (default 24h).
    """
    try:
        redis_client.set(key, json.dumps(value), ex=expire)
    except redis.exceptions.ConnectionError:
        _memory_cache[key] = value

def add_to_history(start: str, target: str):
    """
    Thêm một mục vào lịch sử tìm kiếm toàn cục.
    Add an item to global search history.
    """
    try:
        history_item = json.dumps({"start": start, "target": target})
        redis_client.lpush("global_history", history_item)
        redis_client.ltrim("global_history", 0, 19) # Giữ 20 bản ghi mới nhất
    except redis.exceptions.ConnectionError:
        history_obj = {"start": start, "target": target}
        _memory_history.insert(0, history_obj)
        if len(_memory_history) > 20:
            _memory_history.pop()

def get_history():
    """
    Lấy danh sách lịch sử tìm kiếm toàn cục.
    Get global search history list.
    """
    try:
        items = redis_client.lrange("global_history", 0, -1)
        return [json.loads(item) for item in items]
    except redis.exceptions.ConnectionError:
        return list(_memory_history)
