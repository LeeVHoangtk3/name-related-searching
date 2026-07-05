import redis
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Kết nối đến Redis
# Connect to Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

from collections import OrderedDict

# Bounded LRU Cache for fallback in-memory cache
class BoundedLRUCache:
    def __init__(self, capacity: int = 50000):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: str, default=None):
        if key not in self.cache:
            return default
        self.cache.move_to_end(key)
        return self.cache[key]

    def __setitem__(self, key: str, value: any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# In-memory fallbacks
_memory_cache = BoundedLRUCache(capacity=50000)
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

def get_history_paginated(page: int, size: int):
    """
    Lấy danh sách lịch sử tìm kiếm toàn cục có phân trang sử dụng LLEN và LRANGE.
    Get paginated global search history list using LLEN and LRANGE.
    """
    start_index = (page - 1) * size
    end_index = start_index + size - 1
    try:
        total_items = redis_client.llen("global_history")
        items = redis_client.lrange("global_history", start_index, end_index)
        history = [json.loads(item) for item in items]
        return total_items, history
    except redis.exceptions.ConnectionError:
        total_items = len(_memory_history)
        items = _memory_history[start_index:end_index + 1]
        return total_items, list(items)
