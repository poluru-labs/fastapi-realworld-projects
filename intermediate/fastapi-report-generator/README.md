# FastAPI Report Generator

An intermediate FastAPI service: **JWT auth**, user-owned **report templates**, an admin **metrics catalog**, and synchronous **report runs** that aggregate in-memory data into JSON sections.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). OpenAPI text in `app/main.py` explains ownership and report kinds.

## What you get

| Area | Behavior |
|------|----------|
| Auth | Register, login, refresh, logout (same pattern as other intermediate samples) |
| Templates | CRUD on definitions with kind `sales_summary` or `activity_ledger` |
| Generate | `POST /reports/runs` — filter metrics by period, store structured result |
| Runs | List and fetch your history; other users' ids → **404** |
| Metrics | Admin-only raw catalog feeding generation |
| Errors | **401** / **403** / **404** via `AppError` |

## Report kinds

| Kind | Output |
|------|--------|
| `sales_summary` | Totals grouped by `category` + grand total |
| `activity_ledger` | Chronological metric rows in the window |

## Seed accounts

| Email | Password | Notes |
|-------|----------|--------|
| `admin@example.com` | `AdminPass123!` | Template id `1`, metrics catalog |
| `demo@example.com` | `DemoPass123!` | Ordinary user |

Five metric rows cover Jan–Mar 2026 (total **5590.5** in Q1).

## Quick start

```bash
cd intermediate/fastapi-report-generator
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

### Generate Q1 sales report (admin)

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=AdminPass123!" | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/v1/reports/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "period_start": "2026-01-01T00:00:00+00:00",
    "period_end": "2026-03-31T23:59:59+00:00"
  }'
```

Use `/docs` → **Authorize** with a bearer token from login.

## Swagger walkthrough

1. Login as admin → **Authorize**.
2. **GET /reports/metrics** — inspect seed rows.
3. **POST /reports/runs** — use the example body (template `1`).
4. **GET /reports/runs** — open the stored result sections.
5. **POST /templates** — create an `activity_ledger` template and generate again.

## Layout

```
app/
  schemas/report.py
  repositories/report_repository.py
  services/report_service.py
  api/v1/endpoints/templates.py
  api/v1/endpoints/reports.py
```

## API reference

| Method | Path | Who | Description |
|--------|------|-----|-------------|
| GET/POST | `/api/v1/templates` | Bearer | List / create |
| GET/PATCH/DELETE | `/api/v1/templates/{id}` | Owner | Template CRUD |
| GET | `/api/v1/reports/metrics` | Admin | Metrics catalog |
| GET/POST | `/api/v1/reports/runs` | Bearer | List / generate |
| GET | `/api/v1/reports/runs/{id}` | Owner | Fetch one run |

Auth routes: `/api/v1/auth/*`, users: `/api/v1/users` (admin list).

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-report-generator .
docker run --rm -p 8000:8000 -e SECRET_KEY=your-production-secret fastapi-report-generator
```

Replace in-memory stores before shared deployment.
