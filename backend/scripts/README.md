# M2 — Auth & Core: how anyone can run & verify the backend

A teammate only needs Docker. Everything below is idempotent.

## 1. One-time: create your `.env`
```bash
cp .env.example .env          # from repo root; defaults work for local dev
```

## 2. Bring up the database + backend
```bash
# from repo root
docker compose up -d --build postgres backend
```
- `postgres` runs `database/init.sql` on first boot (creates the schema).
- `backend` serves FastAPI on http://localhost:8000 (Swagger UI at /docs).

## 3. Migrate + seed the demo admin (one command)
```bash
docker compose exec backend bash scripts/bootstrap.sh
```
This runs `alembic upgrade head` (idempotent — coexists with init.sql) and
`python -m scripts.seed_admin` (creates tenant `iisc-demo` + super_admin
`admin@iisc-demo.com`).

## 4. Verify health + auth end-to-end
```bash
# from the host (needs curl)
bash backend/scripts/smoke_test.sh
```
Checks: `/health` reports DB connected · login returns a JWT · wrong password →
401 · `/auth/me` works with the token and 401s without it.

## 5. Run the auth test suite
The `tests/` dir lives at the repo root (not inside the backend image), so run a
one-off container that mounts the whole repo:
```bash
docker compose run --rm -v "$PWD":/repo -w /repo backend pytest tests/test_auth.py -v
```

## Manual curl reference
```bash
# health
curl http://localhost:8000/health

# login -> copy access_token
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@iisc-demo.com","password":"changeme-strong-password"}'

# me (paste the token)
curl http://localhost:8000/auth/me -H "Authorization: Bearer <TOKEN>"
```

## Notes
- Alembic owns the relational/core tables (tenants, users, documents,
  conversations, chat_messages, upload_audit, whatsapp_tenant_map). The pgvector
  tables (`document_chunks`, `ephemeral_chunks`) are owned by `database/init.sql`
  (M7) because their `vector(1024)` columns aren't modelled in the ORM.
- `seed_admin` and the migration are both safe to re-run.
