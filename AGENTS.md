# U-Drop Foundation

## Architecture

Monorepo with three components: Python/FastAPI backend, Vue 3 frontend (git submodule), and C native hash core.

```
server/           ← Real backend entrypoint (server/main.py → uvicorn main:app)
server/api/v1/    ← All API route modules, mounted at /api/v1/{auth,files,messages,share,system,manage,ws}
server/core/      ← Config, native wrapper, rate limiter, upload manager, websocket manager
server/db/        ← Peewee ORM models + repositories + services
server/tasks/     ← asyncio background task system (see server/tasks/AGENTS.md)
backend/sql/      ← SQL migration scripts (auto-applied on startup)
c_core/           ← C/C++ hash core (BLAKE3 + MD5 + thumbnail), compiled to lib/
frontend/         ← Git submodule (https://github.com/Rushyoung/U-drop, branch vista)
server-example/   ← Legacy reference structure, NOT active code
```

Root `main.py` is a placeholder. The real app is `server/main.py`.

## Build & Run

```bash
make init                                    # git submodule update --init --recursive
make vista                                  # frontend: npm install && npm run build
```

**C core compilation** (produces `lib/thumbnail.dll` or `lib/thumbnail.so`):
- Windows: `c_core\compile.bat` — must run from **x64 Native Tools Command Prompt for VS 2022** (WinError 193 otherwise)
- Linux: `cd c_core && ./compile.sh`

**Start backend**: `uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload`
(workdir must be project root so `server.core.config` resolves paths correctly)

## Database

- SQLite (WAL mode), Peewee ORM, located at `udrop.db` (project root)
- Auto-migration on startup: `server/db/bootstrap.py` applies any new `.sql` files from `backend/sql/migrations/` tracked in `schema_migrations` table
- Models defined in `server/db/models.py`, repo pattern: `server/db/repositories/`, service layer: `server/db/services/`
- First run with empty DB auto-bootstraps admin (via `ADMIN_ACCOUNT`/`ADMIN_PASSWORD` env vars) and seeds `sys_settings`

## Key Dependencies

- Python: `uv` as package manager (uv.lock), `pyproject.toml` for deps
- Frontend: Vue 3 + Vite + Tailwind CSS (no test/lint scripts configured)
- Native: `server/core/native_wrapper.py` loads `lib/thumbnail.dll/.so` via ctypes; exposed functions: `CalculateFastFileMD5`, `CalculateFileBLAKE3`, `make_thumbnail`

## Testing

- Tests live in `test/` using pytest with FastAPI TestClient
- `test/conftest.py` mocks `NativeCore` (no real C library needed for tests) and overrides `get_db`/`get_file_service`
- **Note**: conftest references outdated paths (`source/py`, `source/sql`) — these should point to `server/` and `backend/sql/` if tests are to run against current structure

## Gotchas

- `frontend/` is a **git submodule** — changes must be committed in that repo, then the submodule reference updated here
- `deploy/Dockerfile` references `backend/` as WORKDIR and copies `backend/` source — it's **outdated** (actual code is `server/`)
- Config via `pydantic_settings` reads `.env` at project root (see `.env.example`)
- API prefix: all routes are `/api/v1/*`; non-API paths serve the Vue SPA catchall
- `SystemGuard` middleware blocks all `/api/v1/*` (except `/system/status` and `/system/setup`) until system is initialized
- Auth: Bearer token via `Authorization` header; WebSocket and share routes also accept `?token=` query param
