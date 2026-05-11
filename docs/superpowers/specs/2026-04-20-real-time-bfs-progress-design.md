# Spec: Real-time BFS Progress Notifications

Implementing a real-time progress update system for the WikiBFS search using Server-Sent Events (SSE).

## 1. Goal
Users currently wait for a search to finish without any feedback. This change adds a "Scanning Overlay" that shows the BFS process in real-time, including the current node being scanned, total nodes explored, search depth, and elapsed time.

## 2. Architecture

### 2.1 Backend (FastAPI)
- **Endpoint:** `GET /api/search/stream`
  - Accepts `start`, `target`, `max_depth`, `mode`.
  - Checks Redis cache first. If hit, sends a single `complete` event and closes.
  - If miss, initiates an asynchronous BFS process.
- **Service Modification (`bfs_service.py`):**
  - Update `find_path` to accept an optional `on_progress: Callable[[dict], None]` callback.
  - The callback will be triggered when a node is expanded.
- **SSE Streaming:** Uses `sse_starlette.sse.EventSourceResponse` to stream JSON events to the client.

### 2.2 Frontend (React)
- **Search Handling:**
  - Switch from `axios.get` to `EventSource` for the search stream.
  - Maintain a `progress` state: `{ node_id, total_explored, current_depth, elapsed_seconds }`.
- **UI Component (Scanning Overlay):**
  - A centered overlay on the `graph-wrapper` area.
  - Displays a progress spinner and the live search stats.
  - Disappears when search is complete or fails.

## 3. Data Structures

### 3.1 SSE Events
```json
// Progress Update
{
  "event": "progress",
  "data": {
    "node_id": "Q34660",
    "total_explored": 452,
    "current_depth": 2,
    "elapsed_seconds": 1.2
  }
}

// Completion
{
  "event": "complete",
  "data": {
    "status": "success",
    "path": ["Q123", "Q456", "..."]
  }
}

// Error
{
  "event": "error",
  "data": {
    "detail": "No path found"
  }
}
```

## 4. Implementation Steps
1.  **Backend:**
    - Install `sse-starlette`.
    - Modify `bfs_service.py` to support `on_progress`.
    - Implement `streaming_search` endpoint in `routes.py`.
2.  **Frontend:**
    - Create `ProgressOverlay` component.
    - Update `handleSearch` in `App.jsx` to use `EventSource`.
    - Style the overlay in `App.css`.

## 5. Success Criteria
- [ ] Backend correctly streams progress events during BFS.
- [ ] Frontend displays the scanning overlay with live-updating stats.
- [ ] Search still works with caching (immediate results).
- [ ] No regressions in graph rendering or path display.
