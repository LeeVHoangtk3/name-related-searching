# Production Infrastructure Deployment Plan (2026-07-05)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a robust, high-performance, containerized Production environment for the WikiBFS application with Nginx edge reverse proxying, Server-Sent Events (SSE) buffering bypass, and multi-stage container optimization.

**Architecture:** A multi-container Docker Compose setup orchestrated inside an isolated bridge network, routing all incoming client-side and API queries through a unified Nginx instance serving optimized assets.

**Tech Stack:** Docker, Docker Compose, Nginx, Python 3.11 (FastAPI), Node 20 (React).

---

### Task 1: Nginx Edge Gateway Configuration

**Files:**
- Create: `NAME-RELATED-SEARCHING/docker/nginx/nginx.conf`

- [x] **Step 1: Configure server block and proxy policies**
  - Implement static asset routing at root `/` with `try_files` recovery for SPA reloads.
  - Set up `/api/` forwarding to backend container.
  - Disable proxy buffering (`proxy_buffering off`) and cache specifically for `/api/search/stream` to ensure zero-latency delivery of SSE packets.

---

### Task 2: Multi-Container Coordination

**Files:**
- Modify: `NAME-RELATED-SEARCHING/docker-compose.yml`

- [x] **Step 1: Define wikibfs_net bridge network**
- [x] **Step 2: Add healthchecks to Redis**
- [x] **Step 3: Secure mount paths for Nginx configurations**
  - Mount custom configurations at `/etc/nginx/conf.d/default.conf:ro` inside Nginx to prevent master config startup crashes.
- [x] **Step 4: Configure shared assets volume**
  - Mount a named volume `frontend_assets` inside both `frontend` and `nginx` to enable high-speed static asset serving directly from Nginx.

---

### Task 3: Backend Multi-Stage Compilation & Path Resolving

**Files:**
- Modify: `NAME-RELATED-SEARCHING/src/backend/Dockerfile`

- [x] **Step 1: Upgrade runtime base to python:3.11-slim**
- [x] **Step 2: Configure 2-stage build structure**
  - Stage 1 uses `build-essential` to compile wheel dependencies cleanly into user-space `/root/.local`.
  - Stage 2 copies libraries and mounts source code to `/workspace/app`.
- [x] **Step 3: Resolve PYTHONPATH namespace**
  - Set environment variable `PYTHONPATH=/workspace` to guarantee that Uvicorn finds the namespace of package `app` and avoids `ModuleNotFoundError`.

---

### Task 4: Frontend Optimized Build and Conflict Resolution

**Files:**
- Modify: `NAME-RELATED-SEARCHING/src/frontend/src/App.css`
- Create: `NAME-RELATED-SEARCHING/src/frontend/nginx.conf`
- Modify: `NAME-RELATED-SEARCHING/src/frontend/Dockerfile`

- [x] **Step 1: Resolve git merge conflicts in CSS**
  - Remove leftover Git merge conflict boundary markers causing `lightningcss` minification failures.
- [x] **Step 2: Create frontend-specific Nginx optimized settings**
- [x] **Step 3: Set up multi-stage Node build**
  - Optimize cache layers using `npm ci` in Node 20 builder stage.

---

### Task 5: Launch & Status Verification

**Commands:**
- [x] **Step 1: Compile and run containers**
  ```powershell
  docker compose up -d --build
  ```
- [x] **Step 2: Check active health status**
  ```powershell
  docker compose ps
  ```
- [x] **Step 3: Monitor runtime logs for stability**
  ```powershell
  docker compose logs -f backend
  ```
