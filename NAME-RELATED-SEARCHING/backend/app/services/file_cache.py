import json
import os
import time
from typing import Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(filename: str) -> str:
    return os.path.join(CACHE_DIR, filename)


def load_cache(filename: str) -> dict:
    path = _cache_path(filename)

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception as e:
        print(f"⚠️ Cache file corrupted: {filename}")
        print(e)
        return {}



def save_cache(filename: str, data: dict):
    path = _cache_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_cache(filename: str, key: str, ttl: Optional[int] = None):
    cache = load_cache(filename)
    entry = cache.get(key)
    if not entry:
        return None

    if ttl is not None:
        if time.time() - entry["_created_at"] > ttl:
            return None

    return entry["value"]


def set_cache(filename: str, key: str, value: Any):
    cache = load_cache(filename)
    cache[key] = {
        "value": value,
        "_created_at": time.time(),
    }
    save_cache(filename, cache)
