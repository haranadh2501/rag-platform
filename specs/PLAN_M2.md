# M2: Authentication — Status & Plan

> **Module:** M2: Authentication (Auth & Core)
> Scope check against `specs/MODULE_SPEC_M2.md` + the API contract
> (`specs/openapi.yaml`). Branch: `feat/m2-auth-hardening` (base: `dev` @ merged
> PR #3). Legend: ✅ done · 🟡 partial · ❌ missing.

## TL;DR
The core of M2 is **implemented, verified under docker compose, and merged to
dev** (login→JWT→/me, async DB layer, Alembic, idempotent seed, real `/health`
DB ping, integration tests, team scripts). What remains is **hardening**: one
multi-tenant security guard in `/register`, login rate-limiting, a couple of
test gaps, and OpenAPI example polish.

---

## 1. Acceptance Criteria (`MODULE_SPEC_M2` §Acceptance)
| Criterion | State | Notes |
|---|---|---|
| `uvicorn app.main:app --reload` starts without errors | ✅ | Verified — container boots, MCP mounts, no import errors. |
| `alembic upgrade head` creates all tables | 🟡 | Creates the **7 core relational tables** idempotently. The 2 pgvector tables (`document_chunks`, `ephemeral_chunks`) are owned by `database/init.sql` (M7) since their `vector(1024)` cols aren't in the ORM. Strictly "all tables" only when init.sql also runs. |
| `python -m scripts.seed_admin` creates admin | ✅ | Idempotent; verified (1 tenant + 1 super_admin; re-run = no-op). |
| `POST /auth/login` returns JWT | ✅ | Verified via smoke test. |
| `GET /auth/me` returns user w/ valid JWT, 401 without | ✅ | Verified (200 with token, 401 without/garbage). |
| `pytest tests/test_auth.py` passes | 🟡 | Suite exists & passes, but they're **integration** tests needing Postgres (auto-skip if DB down). Missing cases below. |

## 2. Files Owned (`MODULE_SPEC_M2` §Files Owned)
| File | State | Notes |
|---|---|---|
| `backend/app/main.py` | ✅ | `/health` now pings the DB. |
| `backend/alembic/` | ✅ | `env.py` (sync DSN from settings), idempotent `0001_initial`. |
| `backend/app/core/config.py` | ✅ | Added `SYNC_DATABASE_URL` for Alembic. |
| `backend/app/core/security.py` | ✅ | hash/verify + JWT create/decode. `bcrypt==4.0.1` pinned (passlib 1.7.4 compat). |
| `backend/app/core/dependencies.py` | ✅ | `get_current_user`, `require_role` (super_admin bypass). |
| `backend/scripts/seed_admin.py` | ✅ | Real, idempotent. |
| *(added)* `app/core/database.py`, `app/schemas/auth.py` | ✅ | Session layer + Pydantic v2 schemas (not in original list but required). |

## 3. Day-by-Day Deliverables (`MODULE_SPEC_M2` §Plan)
| Day | Deliverable | State |
|---|---|---|
| 1 | Env + branch | ✅ |
| 2 | `main.py` (CORS, middleware, handlers) + Alembic initial migration | ✅ / 🟡 (no custom error handlers; defaults in use) |
| 3 | `seed_admin.py` | ✅ |
| 4 | Auth integration test (login→JWT→protected route) | ✅ |
| 5 | Unit tests (login, register, me, logout, **token expiry**) | ✅ (12 tests; expiry + logout added) |
| 5 | slowapi rate-limit on `/auth/login` (5/min per IP) | ✅ (in-process limiter; 6th attempt → 429) |
| 6 | OpenAPI tags + examples for a clean Swagger demo | ✅ (tags + request/response examples) |

---

## 4. Architecture review (verified against code)
- **Auth architecture is correct** — JWT is stateless (`sub`=user id, `tenant_id`,
  `role`); `get_current_user` decodes + loads the active user; protected routes
  depend on it. ✅
- **Role model is right and consistent** across ORM, OpenAPI, and dependencies:
  `super_admin → admin → user`. ORM defaults `user`; `RegisterRequest.role` enum
  is `{admin, user}`; `require_role` lets `super_admin` bypass. ✅
- **`super_admin` is correctly platform-level / cross-tenant**, created via the
  **seed flow only** (`/register`'s schema can't mint a super_admin). ✅
- **✅ Tenant-scope guard in `/register` — FIXED.** `register`
  ([auth.py](backend/app/api/auth.py)) now rejects with `403` when a non-super_admin
  caller passes a `tenant_id` other than their own (checked before the tenant
  lookup so a tenant admin can't probe other tenants). Covered by
  `test_register_cross_tenant_forbidden_403`. The implementation now fully matches
  the intended multi-tenant design.
  (Secondary consideration, not blocking: an `admin` can still create another
  `admin` within their own tenant — allowed by the current schema; restrict to
  super_admin later if desired.)

---

## 5. Hardening work — this branch (`feat/m2-auth-hardening`) — ✅ DONE
All four items implemented and verified (12/12 tests pass; live 429 confirmed):

1. ✅ **[security] `/register` tenant-scope guard** — non-super_admin → `403` on
   cross-tenant; test `test_register_cross_tenant_forbidden_403`.
2. ✅ **[security] Rate-limit `/auth/login`** — `app/core/rate_limit.py` Limiter
   (key=client IP, `LOGIN_RATE_LIMIT="5/minute"`), wired in `main.py` with the
   `RateLimitExceeded` → 429 handler; test `test_login_rate_limited_429`.
   Also: login body wrapped in try/except → graceful `500` on unexpected errors.
3. ✅ **[tests] Filled gaps** — `test_me_expired_token_401`, `test_logout_with_token`,
   plus the tenant `403`; the `client` fixture now pins a unique IP per test so
   the limiter doesn't bleed across tests.
4. ✅ **[docs/UX] OpenAPI examples** — request/response `examples` on the auth
   schemas (`LoginRequest`, `RegisterRequest`, `UserOut`, `LoginResponse`).

### Next (not started)
- Wrap `/register` DB ops in the same graceful try/except as `/login`.
- Add a `429` / `500` example to the OpenAPI error responses if desired.

### Out of M2 scope (flag only, do not edit here)
- `database/init.sql` ↔ ORM column drift (e.g. `storage_used_bytes`,
  `size_bytes`, `external_id`) — owned by **M7**.
- `CLAUDE.md` run command says `python -m app.scripts.seed_admin`; actual module
  path is `scripts.seed_admin` — doc nit in a root-owned file.
- `/health` reports n8n as `mocked/unchecked` (no real n8n ping) — acceptable
  while `MOCK_N8N=true`.
- `security.py` uses `datetime.utcnow()` (deprecated 3.12+, fine on 3.11).
