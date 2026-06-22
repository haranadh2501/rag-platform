# MODULE_SPEC_M2 — Backend: Auth & Core

**Owner**: Member 2 | **Track**: Backend | **Branch**: `feat/auth`

## Role
FastAPI application scaffold, authentication system, SQLAlchemy models, Alembic migrations, JWT middleware, seed script.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Read `specs/openapi.yaml`. Set up local FastAPI env. Create branch. | ☐ |
| 2 | `backend/app/main.py` — FastAPI app, CORS, middleware, error handlers | ☐ |
| 2 | `backend/alembic/` — init Alembic, create initial migration with all models | ☐ |
| 3 | `backend/scripts/seed_admin.py` — auto-create demo tenant + admin user | ☐ |
| 4 | Auth integration test: full login → JWT → protected route flow works end-to-end | ☐ |
| 5 | Unit tests for auth flows (login, register, me, logout, token expiry) | ☐ |
| 6 | Bug fixes, security hardening | ☐ |

## Files Owned
- `backend/app/main.py`
- `backend/alembic/`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/core/dependencies.py`
- `backend/scripts/seed_admin.py`

## main.py Requirements
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, admin, chat, webhooks, onboarding

app = FastAPI(title="IISc RAG Platform", version="1.0.0")
app.add_middleware(CORSMiddleware, ...)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])

@app.get("/health")
async def health_check(): ...
```

## Alembic Migration Requirements
- Must create ALL tables from `ARCHITECTURE.md` DB schema
- Migration runs with `alembic upgrade head`
- Idempotent — safe to run multiple times

## Seed Script Requirements
```bash
python -m app.scripts.seed_admin
# Creates:
#   Tenant: name="IISc Demo", slug="iisc-demo"
#   User: email=SEED_ADMIN_EMAIL, role="super_admin"
# Reads from .env: SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD, SEED_TENANT_NAME
```

## JWT Middleware
- Every protected route calls `get_current_user()` dependency
- Extracts Bearer token from Authorization header
- Validates with SECRET_KEY + ALGORITHM from config
- Returns `UserOut` object injected into route handler

## Acceptance Criteria
- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `alembic upgrade head` creates all tables in postgres
- [ ] `python -m app.scripts.seed_admin` creates admin user
- [ ] `POST /auth/login` returns JWT
- [ ] `GET /auth/me` returns user with valid JWT, 401 without
- [ ] Unit tests pass: `pytest tests/test_auth.py`


---
<!-- AUTO-APPENDED:SKILLS-V1 -->
## Skills Required
- **Must-have:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 ORM, Alembic migrations, JWT (python-jose), bcrypt, pytest.
- **Nice-to-have:** Async SQLAlchemy, dependency-injection patterns, OAuth2 password flow, slowapi rate-limiting.
- **Soft skills:** Defensive coding (validate every input), security mindset.

## Detailed Step-by-Step Plan
### Day 1 — Environment
1. `cd backend && python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Confirm `uvicorn app.main:app --reload` boots (errors expected before DB is up — that's OK).
4. Create branch `feat/auth` from `main`.

### Day 2 — Alembic + Models
5. Initialize Alembic: `cd backend && alembic init alembic` (skip if folder exists).
6. Configure `alembic.ini` to read `DATABASE_URL` from env: in `alembic/env.py` import `settings` and set `config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)`.
7. Import `app.models.models` in `alembic/env.py` and set `target_metadata = Base.metadata`.
8. Generate initial migration: `alembic revision --autogenerate -m "initial schema"`.
9. Review the generated SQL in `alembic/versions/*.py` — confirm `vector(1024)`, HNSW indexes, all 9 tables present.
10. Apply: `alembic upgrade head`. Verify in Neon console all tables exist.

### Day 3 — Auth + Seed
11. Implement `app/core/security.py` helpers: `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`.
12. Implement `app/core/dependencies.py`: `get_current_user`, `require_role(role)`.
13. Wire `app/api/auth.py` endpoints: `POST /login`, `POST /register`, `GET /me`, `POST /logout`.
14. Build `scripts/seed_admin.py`: creates 1 tenant + 1 super_admin user from env vars; idempotent.
15. Run end-to-end: `python -m scripts.seed_admin` → `curl -X POST /auth/login` → save JWT → `curl -H "Authorization: Bearer " /auth/me`.

### Fetch List of user  
16. Implement `app/api/admin.py` endpoints: `GET /users` if tenant is present then teneant as serach paramter if not present then show pagination based list of users 


### Day 4-5 — Tests + Hardening
16. `tests/test_auth.py`: login success, login wrong password (401), expired token (401), valid /me, role guard.
17. Add slowapi rate-limit to `/auth/login` (5/min per IP).
18. Run `pytest -v` → target 90 %+ coverage on auth module.

### Day 6 — Polish
19. Add OpenAPI tags + examples so Swagger UI is presentable for demo.

## Learning Resources
- FastAPI security tutorial: https://fastapi.tiangolo.com/tutorial/security/
- SQLAlchemy 2.0 ORM: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- Alembic autogenerate caveats: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
