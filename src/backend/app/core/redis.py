import redis
import json
from app.core.config import settings

# Kết nối đến Redis
# Connect to Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_cache(key: str):
    """
    Lấy dữ liệu từ cache Redis.
    Get data from Redis cache.
    """
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cache(key: str, value: any, expire: int = 86400):
    """
    Lưu dữ liệu vào cache Redis với thời gian hết hạn (mặc định 24h).
    Save data to Redis cache with expiration (default 24h).
    """
    redis_client.set(key, json.dumps(value), ex=expire)

def add_to_history(start: str, target: str):
    """
    Thêm một mục vào lịch sử tìm kiếm toàn cục.
    Add an item to global search history.
    """
    history_item = json.dumps({"start": start, "target": target})
    redis_client.lpush("global_history", history_item)
    redis_client.ltrim("global_history", 0, 19) # Giữ 20 bản ghi mới nhất (Keep 20 latest records)

def get_history():
    """
    Lấy danh sách lịch sử tìm kiếm toàn cục.
    Get global search history list.
    """
    items = redis_client.lrange("global_history", 0, -1)
    return [json.loads(item) for item in items]
