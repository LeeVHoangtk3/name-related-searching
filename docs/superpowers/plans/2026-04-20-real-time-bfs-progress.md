# Real-time BFS Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real-time progress overlay to the WikiBFS search, showing live stats as the BFS algorithm explores nodes.

**Architecture:** 
- Use Server-Sent Events (SSE) to stream updates from the backend to the frontend.
- Modify the BFS service to accept a progress callback.
- Implement a new streaming endpoint in FastAPI using `sse-starlette`.
- Update the React frontend to use `EventSource` and display a scanning overlay.

**Tech Stack:** FastAPI, sse-starlette, React, EventSource API.

---

### Task 1: Backend Dependencies & Service Modification

**Files:**
- Modify: `NAME-RELATED-SEARCHING/backend/requirements.txt`
- Modify: `NAME-RELATED-SEARCHING/backend/app/services/bfs_service.py`

- [ ] **Step 1: Add sse-starlette to requirements.txt**

```text
fastapi
uvicorn
requests
pydantic-settings
python-dotenv
redis
sse-starlette
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r NAME-RELATED-SEARCHING/backend/requirements.txt`

- [ ] **Step 3: Modify find_path to support on_progress callback**

```python
# NAME-RELATED-SEARCHING/backend/app/services/bfs_service.py

def find_path(
    start: str,
    target: str,
    get_neighbors: Callable[[str], List[str]],
    max_depth: int,
    max_nodes: int = 15000,
    max_seconds: Optional[float] = None,
    on_progress: Optional[Callable[[dict], None]] = None, # Add this
) -> Optional[List[str]]:
    # ... inside expand_one_layer loop ...
    for _ in range(len(queue)):
        enforce_limits()
        current = queue.popleft()
        
        # Trigger progress callback
        if on_progress:
            on_progress({
                "node_id": current,
                "total_explored": len(forward_parent) + len(backward_parent),
                "current_depth": own_depth[current],
                "elapsed_seconds": round(time.monotonic() - started_at, 2)
            })
        # ... rest of the code ...
```

- [ ] **Step 4: Commit backend service changes**

```bash
git add NAME-RELATED-SEARCHING/backend/requirements.txt NAME-RELATED-SEARCHING/backend/app/services/bfs_service.py
git commit -m "feat(backend): add sse-starlette and progress callback to bfs_service"
```

### Task 2: Implement Streaming Endpoint

**Files:**
- Modify: `NAME-RELATED-SEARCHING/backend/app/api/routes.py`

- [ ] **Step 1: Import EventSourceResponse and update imports**

```python
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
```

- [ ] **Step 2: Implement /search/stream endpoint**

```python
@router.get("/search/stream")
async def search_path_stream(
    start: str = Query(...),
    target: str = Query(...),
    max_depth: int = Query(8),
    mode: str = Query("fast"),
):
    async def event_generator():
        start_id = resolve_entity_input(start)
        target_id = resolve_entity_input(target)
        
        # Check cache first
        cache_key = f"path:{start_id}:{target_id}"
        cached_path = get_cache(cache_key)
        if cached_path:
            yield {
                "event": "complete",
                "data": json.dumps({"status": "success", "path": cached_path, "source": "cache"})
            }
            return

        # Prepare neighbor fetcher
        # (Copy logic from search_path for mode=fast/deep)
        
        queue = asyncio.Queue()

        def on_progress(data):
            queue.put_nowait({"event": "progress", "data": json.dumps(data)})

        # Run BFS in a separate thread to not block event loop
        loop = asyncio.get_event_loop()
        def run_bfs():
            try:
                path = find_path(
                    start=start_id,
                    target=target_id,
                    get_neighbors=neighbor_fetcher,
                    max_depth=effective_depth,
                    max_nodes=max_nodes,
                    on_progress=on_progress
                )
                if path:
                    set_cache(cache_key, path)
                    queue.put_nowait({"event": "complete", "data": json.dumps({"status": "success", "path": path})})
                else:
                    queue.put_nowait({"event": "complete", "data": json.dumps({"status": "no_path", "path": []})})
            except Exception as e:
                queue.put_nowait({"event": "error", "data": json.dumps({"detail": str(e)})})
            finally:
                queue.put_nowait(None) # Signal end

        asyncio.create_task(loop.run_in_executor(None, run_bfs))

        while True:
            msg = await queue.get()
            if msg is None:
                break
            yield msg

    return EventSourceResponse(event_generator())
```

- [ ] **Step 3: Commit streaming endpoint**

```bash
git add NAME-RELATED-SEARCHING/backend/app/api/routes.py
git commit -m "feat(backend): implement /search/stream SSE endpoint"
```

### Task 3: Frontend UI Components

**Files:**
- Create: `NAME-RELATED-SEARCHING/frontend/src/components/ProgressOverlay.jsx`
- Modify: `NAME-RELATED-SEARCHING/frontend/src/App.css`

- [ ] **Step 1: Create ProgressOverlay component**

```javascript
import React from 'react';
import { Loader2 } from 'lucide-react';

const ProgressOverlay = ({ progress }) => {
  if (!progress) return null;
  return (
    <div className="progress-overlay">
      <div className="progress-card">
        <Loader2 className="animate-spin" size={32} color="#bb86fc" />
        <div className="progress-info">
          <h3>Scanning: <span className="highlight">{progress.node_id}</span></h3>
          <div className="progress-stats">
            <span>Nodes: {progress.total_explored}</span>
            <span>Depth: {progress.current_depth}</span>
            <span>Time: {progress.elapsed_seconds}s</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressOverlay;
```

- [ ] **Step 2: Add styles to App.css**

```css
.progress-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(18, 18, 18, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  backdrop-filter: blur(4px);
}

.progress-card {
  background: var(--bg-card);
  padding: 24px 32px;
  border-radius: 12px;
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.progress-info {
  text-align: center;
}

.progress-info h3 {
  font-size: 0.9rem;
  color: var(--text-dim);
  margin-bottom: 8px;
}

.highlight {
  color: var(--primary);
  font-family: monospace;
}

.progress-stats {
  display: flex;
  gap: 12px;
  font-size: 0.75rem;
  color: var(--text-dim);
}
```

- [ ] **Step 3: Commit frontend components**

```bash
git add NAME-RELATED-SEARCHING/frontend/src/components/ProgressOverlay.jsx NAME-RELATED-SEARCHING/frontend/src/App.css
git commit -m "feat(frontend): add ProgressOverlay component and styles"
```

### Task 4: Integrate EventSource in App.jsx

**Files:**
- Modify: `NAME-RELATED-SEARCHING/frontend/src/App.jsx`

- [ ] **Step 1: Import ProgressOverlay and add progress state**

```javascript
import ProgressOverlay from './components/ProgressOverlay';
// ...
const [progress, setProgress] = useState(null);
```

- [ ] **Step 2: Update handleSearch to use EventSource**

```javascript
const handleSearch = () => {
  const startValue = startSelection?.qid || startInput.trim();
  const targetValue = targetSelection?.qid || targetInput.trim();
  if (!startValue || !targetValue) return;

  setLoading(true);
  setError(null);
  setProgress({ node_id: 'Initializing...', total_explored: 0, current_depth: 0, elapsed_seconds: 0 });

  const url = new URL(`${API_BASE_URL}/search/stream`);
  url.searchParams.append('start', startValue);
  url.searchParams.append('target', targetValue);
  url.searchParams.append('max_depth', SEARCH_MAX_DEPTH);
  url.searchParams.append('mode', SEARCH_MODE);

  const eventSource = new EventSource(url.toString());

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    setProgress(data);
  });

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data);
    if (data.status === 'success') {
      const foundPath = data.path;
      setPath(foundPath);
      const nodes = foundPath.map(id => ({ id, name: id }));
      const links = [];
      for (let i = 0; i < foundPath.length - 1; i++) {
        links.push({ source: foundPath[i], target: foundPath[i+1] });
      }
      setGraphData({ nodes, links });
      fetchGlobalHistory();
    } else {
      setError('Không tìm thấy đường nối.');
      setGraphData({ nodes: [], links: [] });
    }
    eventSource.close();
    setLoading(false);
    setProgress(null);
  });

  eventSource.addEventListener('error', (e) => {
    setError('Đã xảy ra lỗi khi kết nối server.');
    eventSource.close();
    setLoading(false);
    setProgress(null);
  });
};
```

- [ ] **Step 3: Render ProgressOverlay inside graph-wrapper**

```jsx
<div className="graph-wrapper">
  {loading && <ProgressOverlay progress={progress} />}
  {/* ... existing graph code ... */}
</div>
```

- [ ] **Step 4: Commit integration changes**

```bash
git add NAME-RELATED-SEARCHING/frontend/src/App.jsx
git commit -m "feat(frontend): integrate EventSource for real-time progress"
```

### Task 5: Final Verification

- [ ] **Step 1: Restart backend and frontend**
- [ ] **Step 2: Test a new search (cache miss)** and verify overlay updates live.
- [ ] **Step 3: Test a cached search (cache hit)** and verify it finishes instantly.
- [ ] **Step 4: Test search with no path found.**
