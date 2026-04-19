# Redis Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Redis for result caching and global search history in WikiBFS.

**Architecture:** Use a "Cache Aside" pattern for Wikidata queries and a Redis List for global history.

**Tech Stack:** Redis, redis-py, FastAPI, React.

---

### Task 1: Update Dependencies and Configuration

**Files:**
- Modify: `NAME-RELATED-SEARCHING/backend/requirements.txt`
- Modify: `NAME-RELATED-SEARCHING/backend/app/core/config.py`

- [ ] **Step 1: Update requirements.txt**
```text
fastapi
uvicorn
requests
pydantic-settings
python-dotenv
redis
```

- [ ] **Step 2: Update config.py with Redis settings**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "WikiBFS API"
    WIKIDATA_ENDPOINT: str = "https://query.wikidata.org/sparql"
    USER_AGENT: str = "WikiBFS/1.0 (https://github.com/LeeVHoangtk3/name-related-searching; contact: leviethoangtk3@gmail.com)"
    TIMEOUT: int = 20
    DEFAULT_LIMIT: int = 50
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Commit**
```bash
git add NAME-RELATED-SEARCHING/backend/requirements.txt NAME-RELATED-SEARCHING/backend/app/core/config.py
git commit -m "feat: add redis dependencies and config"
```

---

### Task 2: Create Redis Client Module

**Files:**
- Create: `NAME-RELATED-SEARCHING/backend/app/core/redis.py`

- [ ] **Step 1: Create Redis client initialization**
```python
import redis
import json
from app.core.config import settings

# Kết nối đến Redis
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_cache(key: str):
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cache(key: str, value: any, expire: int = 86400):
    redis_client.set(key, json.dumps(value), ex=expire)

def add_to_history(start: str, target: str):
    history_item = json.dumps({"start": start, "target": target})
    redis_client.lpush("global_history", history_item)
    redis_client.ltrim("global_history", 0, 19) # Giữ 20 bản ghi mới nhất

def get_history():
    items = redis_client.lrange("global_history", 0, -1)
    return [json.loads(item) for item in items]
```

- [ ] **Step 2: Commit**
```bash
git add NAME-RELATED-SEARCHING/backend/app/core/redis.py
git commit -m "feat: implement redis client and helper functions"
```

---

### Task 3: Integrate Caching into BFS Service and Routes

**Files:**
- Modify: `NAME-RELATED-SEARCHING/backend/app/api/routes.py`
- Modify: `NAME-RELATED-SEARCHING/backend/app/services/neighbor_wikidata.py`

- [ ] **Step 1: Update neighbor_wikidata.py to use cache**
```python
from typing import List
from app.clients.wikidata import wikidata_client
from app.core.config import settings
from app.core.redis import get_cache, set_cache

def get_neighbors(wikidata_id: str) -> List[str]:
    cache_key = f"neighbors:{wikidata_id}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    query = f"SELECT ?neighbor WHERE {{ wd:{wikidata_id} ?p ?neighbor . ?neighbor wdt:P31 wd:Q5 . }} LIMIT {settings.DEFAULT_LIMIT}"
    bindings = wikidata_client.query(query)

    neighbors = [item["neighbor"]["value"].split("/")[-1] for item in bindings if "neighbor" in item]
    
    set_cache(cache_key, neighbors, expire=172800) # 48h
    return neighbors
```

- [ ] **Step 2: Update routes.py to handle path caching and history**
```python
from fastapi import APIRouter, HTTPException, Query
from app.services.bfs_service import find_path
from app.services.neighbor_wikidata import get_neighbors
from app.core.redis import get_cache, set_cache, add_to_history, get_history

router = APIRouter()

@router.get("/search")
def search_path(start: str = Query(...), target: str = Query(...), max_depth: int = 3):
    cache_key = f"path:{start}:{target}"
    cached = get_cache(cache_key)
    if cached:
        add_to_history(start, target)
        return {"status": "success", "path": cached, "source": "cache"}

    path = find_path(start, target, get_neighbors, max_depth)
    if path:
        set_cache(cache_key, path)
        add_to_history(start, target)
        return {"status": "success", "path": path, "source": "api"}
    
    return {"status": "no_path", "path": []}

@router.get("/history")
def get_global_history():
    return {"history": get_history()}
```

- [ ] **Step 3: Commit**
```bash
git add NAME-RELATED-SEARCHING/backend/app/api/routes.py NAME-RELATED-SEARCHING/backend/app/services/neighbor_wikidata.py
git commit -m "feat: integrate redis caching and history into API"
```

---

### Task 4: Update Frontend to use Global History

**Files:**
- Modify: `NAME-RELATED-SEARCHING/frontend/src/App.jsx`

- [ ] **Step 1: Update App.jsx to fetch global history on mount**
```javascript
// ... existing imports
import { useEffect } from 'react';

// ... inside App component
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/history`);
        setHistory(response.data.history);
      } catch (err) {
        console.error("Failed to fetch history", err);
      }
    };
    fetchHistory();
    // Poll mỗi 30s để cập nhật lịch sử toàn cục
    const interval = setInterval(fetchHistory, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = async () => {
    // ... logic cũ ...
    // Sau khi search thành công, fetch lại history
    const historyRes = await axios.get(`${API_BASE_URL}/history`);
    setHistory(historyRes.data.history);
  };
```

- [ ] **Step 2: Commit**
```bash
git add NAME-RELATED-SEARCHING/frontend/src/App.jsx
git commit -m "feat: display global history in frontend"
```
