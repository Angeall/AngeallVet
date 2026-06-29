# CLAUDE.md

Guidance for working in this repository. Keep it current when architecture or commands change.

## What this is

**AngeallVet** — a veterinary practice-management system (PMS). Monorepo:
- `backend/` — Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2, PostgreSQL, Alembic.
- `frontend/` — React 18 (Vite 8), React Router 6, Recharts, FullCalendar.
- Orchestrated with Docker Compose behind a Caddy reverse proxy.

UI text, error messages and most comments are in **French** — match that in user-facing strings.

## Commands

**Backend** (run from `backend/`, use the venv):
```bash
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows path
venv/Scripts/python.exe -m pytest                            # tests (in-memory SQLite, no external services)
uvicorn app.main:app --reload                                # dev server :8000  (Swagger at /api/docs)
python -m app.seed_demo                                      # demo data (needs PocketBase up + superuser)
```
Migrations run automatically at startup; manual: `alembic upgrade head`.

**Frontend** (run from `frontend/`):
```bash
npm install
npm run dev          # Vite dev server :3000
npm run build        # production build -> build/
npm run e2e          # Playwright e2e (run `npx playwright install chromium` once)
```
For local dev without the proxy, create `frontend/.env.local` with `VITE_API_URL=http://localhost:8000/api/v1` and `VITE_POCKETBASE_URL=http://localhost:8090`.

**Docker** (whole stack): `docker compose up -d`, then create the PocketBase superuser (see README) and `docker compose restart backend`. App at `http://app.angeallvet.localhost`.

## Architecture (read before touching auth or DB routing)

**Multi-tenant.** A central *registry* database holds only the `tenants` table; each tenant has its **own PostgreSQL database** (all clinic data + users/RBAC/notifications) and its **own PocketBase instance** (auth). A "default" tenant fallback keeps single-clinic / dev / tests working with a single database.

**Tenant resolution = sub-domain.** `TenantMiddleware` (pure ASGI, in `app/main.py`) resolves the tenant from the `Host`/`X-Forwarded-Host` and stashes a `TenantContext` on `request.scope["tenant_ctx"]`. DB/auth dependencies read it back from the scope.
- ⚠️ Do **not** use `ContextVar` for request-scoped tenant state: values set in middleware don't reliably reach Starlette's thread-pool endpoints. Always go through `request.scope`.

**Auth = tenant-local PocketBase + app JWT exchange** (replaced Supabase):
1. Browser logs in directly against the tenant's PocketBase (`frontend/src/services/pocketbase.js`, `AuthContext.jsx`).
2. Frontend sends the PB token to `POST /auth/session`; the backend verifies it via PB `auth-refresh` (`app/core/pocketbase.py`) and mints an **application JWT** signed with a per-tenant secret (`app/core/security.py` `create_app_token`; secret derived from `APP_SECRET_KEY`+slug in `app/core/tenancy.py`).
3. All API calls send that app JWT; `get_current_user` verifies it with the tenant secret and loads the profile (`User.pb_user_id`).

**DB session dependencies:**
- `get_tenant_db` / `get_request_db` — session routed to the request's tenant DB (read from scope). Use for all tenant data.
- `get_central_db` — the registry DB; use only for `tenants` management endpoints.
- `get_current_user` (in `app/core/security.py`) — auth; `require_roles(...)` for RBAC.

**Schema management.** `_ensure_schema()` in `app/main.py` runs at startup on the central DB and every active tenant DB: `create_all` + a `_pending_columns` list of `ALTER TABLE ADD COLUMN` + a `_pending_renames` list. Alembic also runs (non-blocking). **When you add a column to a model, also add it to `_pending_columns`** so pre-existing databases get it. Performance indexes (pg_trgm search + composites) live in `app/core/db_indexes.py` and are applied the same way (Postgres-only, AUTOCOMMIT) plus migration 009 — single source of truth, so add new index DDL there.

## Gotchas

- **Vite + PocketBase:** the PB SDK has a method named `import`, which Vite's dev import-analysis mistakes for a dynamic `import()` and corrupts → dev server crashes with a blank page. The `pocketbaseImportMethodFix` plugin + `optimizeDeps.exclude: ['pocketbase']` in `frontend/vite.config.js` fix it. **Do not remove them.** (Production rollup build is unaffected.)
- `POST /auth/register` is **admin-only** (creates a PocketBase user + local profile).
- Missing-credentials requests return **401** (FastAPI `HTTPBearer`), role-forbidden returns **403**.
- Backend tests use in-memory SQLite and mock PocketBase; Playwright tests mock all network (`page.route`) — neither needs a running backend/DB/PocketBase.

## Testing expectations

Before considering backend work done: `pytest` green (currently 120 tests). For frontend behavior changes: keep `npm run e2e` green and add a case in `frontend/e2e/` for new critical flows.
