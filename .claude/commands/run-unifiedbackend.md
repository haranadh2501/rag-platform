---
name: run-unifiedbackend
description: Start the FastAPI backend server with uvicorn on port 8000.
allowed-tools: Bash(cd backend*), Bash(uvicorn*), Bash(python*), Bash(pip*)
---

# run-backend

Start the FastAPI backend for the rag-platform project.

## 1. Pre-flight checks

Check requirements are installed:
```bash
pip show fastapi
```

If not found, run pip install -r backend/requirements.txt first.

Check .env exists:
```bash
test -f .env
```
If missing, tell the user to copy .env.example to .env and fill in secrets. Stop.

2. Start the server
```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Stream the output so the user can see startup logs and any errors live.

3. Confirm ready
When you see Application startup complete in the output, tell the user:

Backend is live at http://localhost:8000
API docs at http://localhost:8000/docs


