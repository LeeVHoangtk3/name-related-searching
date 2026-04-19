# Virtual Environment Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup a Python virtual environment for the backend and update related docs/configs.

**Architecture:** Standard Python `venv` setup.

**Tech Stack:** Python 3.

---

### Task 1: Create Virtual Environment and Update .gitignore

**Files:**
- Create: `NAME-RELATED-SEARCHING/backend/venv/` (via command)
- Modify: `.gitignore`

- [ ] **Step 1: Create virtual environment**
Run: `python3 -m venv NAME-RELATED-SEARCHING/backend/venv`

- [ ] **Step 2: Update .gitignore to exclude venv**
```text
# Python virtual environment
NAME-RELATED-SEARCHING/backend/venv/
venv/
.venv/
```

- [ ] **Step 3: Commit**
```bash
git add .gitignore
git commit -m "chore: setup virtual environment and update .gitignore"
```

---

### Task 2: Update README with Venv Instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update Backend setup instructions**
```markdown
### 1. Backend
Yêu cầu Python 3.9+
```bash
cd NAME-RELATED-SEARCHING/backend
# Tạo và kích hoạt môi trường ảo
python3 -m venv venv
source venv/bin/activate  # Trên Linux/macOS
# venv\Scripts\activate  # Trên Windows

# Cài đặt dependencies
pip install -r requirements.txt
uvicorn app.main:app --reload
```
```

- [ ] **Step 2: Commit**
```bash
git add README.md
git commit -m "docs: add virtual environment instructions to README"
```
