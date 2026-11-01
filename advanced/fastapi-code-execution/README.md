# Code execution API

Advanced FastAPI sample: **policy limits**, **runner-authenticated** run submission,
**idempotent** creates, AST validation, and timeout-bound in-process Python execution.
OpenAPI narratives live in `app/main.py`; use `/docs` to explore headers and statuses.

> **Not production-safe.** Runs use restricted `exec` in a thread pool, not OS-level
> isolation. Read the safety section in `/docs` before extending this design.

## Auth headers

| Header | Role |
|--------|------|
| `X-Runner-Key` | Submit runs |
| `X-Admin-Key` | Policy CRUD, list runs, read any run |
| `Idempotency-Key` | Required on `POST /execution/runs` |

Defaults in `.env.example`: `dev-admin-key-change-me`, `dev-runner-key-change-me`.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/execution/policy` | Admin |
| PATCH | `/api/v1/execution/policy` | Admin |
| POST | `/api/v1/execution/runs` | Runner + idempotency |
| GET | `/api/v1/execution/runs` | Admin |
| GET | `/api/v1/execution/runs/{id}` | Runner or admin |

Run statuses: `completed`, `failed`, `timeout`, `rejected`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload
```

## Walkthrough

1. **Authorize admin** in Swagger (`Authorize` → `X-Admin-Key`).
2. **Read policy** — `GET /api/v1/execution/policy` (8 KiB source, 2 s timeout, `python`).
3. **Submit a run** — authorize runner key, then:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/execution/runs \
  -H "Content-Type: application/json" \
  -H "X-Runner-Key: dev-runner-key-change-me" \
  -H "Idempotency-Key: demo-run-1" \
  -d '{"language":"python","source":"print(sum(range(5)))"}'
```

4. **Fetch result** — `GET /api/v1/execution/runs/{id}` with runner or admin key.
5. **Audit** — `GET /api/v1/execution/runs` with admin key (includes seed run).

Seed idempotency key `seed-run-hello` returns the preloaded completed run on re-submit.

## Layout

```
app/core/sandbox_runner.py   # AST validation + restricted exec
app/services/execution_service.py
app/api/v1/endpoints/runs.py
app/api/v1/endpoints/policy.py
```

## Tests

```bash
pytest -v
ruff check app tests
```

Tests bootstrap schema + seed in `tests/conftest.py` (in-memory SQLite).
