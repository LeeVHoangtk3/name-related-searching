# Deployment Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare WikiBFS for free deployment on Render (Backend) and Vercel (Frontend).

**Architecture:** Create Docker configuration for Python backend and environment variable support for React frontend.

**Tech Stack:** Docker, FastAPI, Vite, React.

---

### Task 1: Backend Deployment Setup (Render)

**Files:**
- Create: `NAME-RELATED-SEARCHING/backend/Dockerfile`
- Create: `NAME-RELATED-SEARCHING/backend/.dockerignore`

- [ ] **Step 1: Create Dockerfile for FastAPI**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Cài đặt các dependencies hệ thống cần thiết
# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Sao chép requirements và cài đặt
# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn
# Copy source code
COPY . .

# Chạy ứng dụng với uvicorn
# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create .dockerignore**
```text
__pycache__
*.pyc
.env
.git
.gitignore
```

- [ ] **Step 3: Commit**
```bash
git add NAME-RELATED-SEARCHING/backend/Dockerfile NAME-RELATED-SEARCHING/backend/.dockerignore
git commit -m "deploy: add Dockerfile and .dockerignore for backend"
```

---

### Task 2: Frontend Environment Variable Support (Vercel)

**Files:**
- Modify: `NAME-RELATED-SEARCHING/frontend/src/App.jsx`
- Create: `NAME-RELATED-SEARCHING/frontend/.env.example`

- [ ] **Step 1: Update App.jsx to use VITE_API_BASE_URL**
```javascript
// Thay đổi dòng: const API_BASE_URL = 'http://localhost:8000/api';
// Thành logic sử dụng biến môi trường:
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
```

- [ ] **Step 2: Create .env.example for frontend**
```text
VITE_API_BASE_URL=https://your-backend-on-render.com/api
```

- [ ] **Step 3: Commit**
```bash
git add NAME-RELATED-SEARCHING/frontend/src/App.jsx NAME-RELATED-SEARCHING/frontend/.env.example
git commit -m "deploy: support environment variables for frontend API URL"
```

---

### Task 3: Final README Updates for Deployment

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Deployment section to README.md**
```markdown
## Triển khai (Deployment)

### Backend (Render)
1. Kết nối repo GitHub với Render.
2. Chọn "Web Service", Runtime là "Docker".
3. Thêm Environment Variable: `REDIS_URL` (từ Upstash).

### Frontend (Vercel)
1. Kết nối repo GitHub với Vercel.
2. Thêm Environment Variable: `VITE_API_BASE_URL` (URL của Render + `/api`).
```

- [ ] **Step 2: Commit**
```bash
git add README.md
git commit -m "docs: add deployment instructions to README"
```
