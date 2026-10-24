# FastAPI Rate Limiter

An advanced FastAPI **rate limiting control plane**: admin **policies** (fixed window), **clients** with hashed secrets, and **quota** check/consume for SDKs. Async SQLAlchemy, Alembic, structured logs, and health probes match the other advanced samples.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

## What you get

| Area | Behavior |
|------|----------|
| Policies | Admin CRUD lifecycle; pause/resume without losing counters |
| Clients | Provision with one-time `client_key`; bind to a policy |
| Quota | `check` (dry-run) and `consume` (increment + idempotency) |
| Headers | `X-Admin-Key`, `X-Client-Id`, `X-Client-Key`, `Idempotency-Key` |
| Algorithm | Fixed window per `(client, subject_key)` stored in SQL |
| Errors | **401** / **403** / **404** / **409** / **429** via `AppError` or quota body |

## Seed

| Policy | Limit | Client | X-Client-Key |
|--------|-------|--------|----------------|
| `public-api` | 10 / 60s | `mobile-app` | `seed-client-mobile-app` |

Subject `device-abc` starts at **3/10** in the current window.

## Quick start

```bash
cd advanced/fastapi-rate-limiter
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload
```

### Check and consume

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/quota/check \
  -H "X-Client-Id: mobile-app" \
  -H "X-Client-Key: seed-client-mobile-app" \
  -H "Content-Type: application/json" \
  -d '{"subject_key":"device-abc","cost":1}'

curl -s -X POST http://127.0.0.1:8000/api/v1/quota/consume \
  -H "X-Client-Id: mobile-app" \
  -H "X-Client-Key: seed-client-mobile-app" \
  -H "Idempotency-Key: demo-1" \
  -H "Content-Type: application/json" \
  -d '{"subject_key":"device-abc","cost":1}'
```

## Swagger walkthrough

1. Authorize admin routes with `X-Admin-Key` from `.env`.
2. **GET /clients/mobile-app/usage** — seed counters.
3. **POST /quota/check** — client headers only.
4. **POST /quota/consume** — add `Idempotency-Key`; retry to see idempotent replay.
5. **POST /policies** and **POST /clients** — provision a new pair.

## Layout

```
app/
  core/windows.py              # fixed-window boundaries
  models/rate_limiting.py
  services/policy_service.py
  services/client_service.py
  services/quota_service.py
  api/v1/endpoints/policies.py
  api/v1/endpoints/clients.py
  api/v1/endpoints/quota.py
alembic/versions/001_initial_rate_limiter.py
```

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET/POST | `/api/v1/policies` | Admin | List / create |
| GET | `/api/v1/policies/{key}` | Admin | Detail |
| POST | `/api/v1/policies/{key}/pause` | Admin | Pause |
| POST | `/api/v1/policies/{key}/resume` | Admin | Resume |
| GET/POST | `/api/v1/clients` | Admin | List / provision |
| GET | `/api/v1/clients/{key}` | Admin | Metadata |
| GET | `/api/v1/clients/{key}/usage` | Admin | Window snapshot |
| POST | `/api/v1/quota/check` | Client headers | Dry-run |
| POST | `/api/v1/quota/consume` | Client + idempotency | Increment |

## Tests and lint

```bash
pytest -v
ruff check app tests alembic
```

Tests bootstrap in-memory SQLite and seed automatically.

## Docker

```bash
docker compose up --build
```
