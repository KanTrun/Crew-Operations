# ca-api

FastAPI service for NHỊP QUÁN.

## Run (dev)

```bash
cd apps/api
uv run uvicorn ca_api.interfaces.http.main:app --reload --port 8000
```

## Auth

Session tokens come from `POST /api/v1/auth/login` (stored in `data/quan.db`).

| User | Password | Role | nv_id |
|------|----------|------|-------|
| lan | `nhipquan` | quan_ly | nv_01 |
| minh | `nhipquan` | nhan_vien | nv_03 |
| hung | `nhipquan` | chu_quan | nv_02 |

Pass the returned token as `Authorization: Bearer <token>`.

## Endpoints

- `GET /health`
- `POST /api/v1/auth/login`
- `GET /api/v1/contracts`
- `GET /api/v1/lich-tuan?tuan=2026-W34` — weekly roster
- `POST /api/v1/lich-tuan/pin` — pin/unpin (quan_ly or chu_quan)

## Database migrations (Alembic)

```bash
# Install deps
uv sync

# Set DB URL (or export DATABASE_URL env var)
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nhip_quan

# Apply all migrations
cd apps/api
uv run alembic -c alembic/alembic.ini upgrade head

# Roll back one step
uv run alembic -c alembic/alembic.ini downgrade -1

# Create a new migration
uv run alembic -c alembic/alembic.ini revision -m "describe_change"
```

Tables created by `0001_initial_tables`:
- `nhan_vien` — staff records
- `ca` — shift definitions
- `lich_tuan_phan_cong` — weekly assignment with pinned flag

## Tests

```bash
cd apps/api
uv run pytest tests/
```
