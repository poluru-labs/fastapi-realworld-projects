# FastAPI Usage Billing

Advanced FastAPI service for **metered usage**, **subscriptions**, and **invoice generation** on async SQLAlchemy (SQLite locally, Postgres via Compose). OpenAPI at `/docs` documents admin vs customer credentials, idempotent ingestion, and how overage is calculated.

## What is wired

| Piece | Where | Role |
|-------|--------|------|
| Settings | `app/core/config.py` | `ADMIN_API_KEY`, `API_KEY_PEPPER`, database URL |
| Request id | `app/middleware/request_context.py` | Echoes `X-Request-ID`; usage rows store it |
| DB session | `app/api/deps.py` | Commits on success, rolls back on errors |
| Models | `app/models/billing.py` | Customers, meters, plans, usage, invoices |
| Seed | `app/db/seed.py` | `api_calls` + `tokens` meters, `starter` plan |
| Migrations | `alembic/versions/` | `alembic upgrade head` before run |

## Credentials

| Header | Who | Used for |
|--------|-----|----------|
| `X-Admin-Key` | Platform | Customers, subscriptions, invoice admin routes |
| `X-Api-Key` | Customer | `POST /usage/events`, `/me/*` |

Customer keys are returned once from `POST /customers`; only a hash is stored (`app/core/security.py`).

## End-to-end flow

```bash
# 1) Catalog (public)
curl -s http://127.0.0.1:8000/api/v1/meters
curl -s http://127.0.0.1:8000/api/v1/plans

# 2) Create customer (admin)
curl -s -X POST http://127.0.0.1:8000/api/v1/customers \
  -H "X-Admin-Key: dev-admin-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"external_id":"acct_1","name":"Acme"}'

# 3) Subscribe to starter
curl -s -X POST http://127.0.0.1:8000/api/v1/customers/1/subscriptions \
  -H "X-Admin-Key: dev-admin-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"plan_code":"starter"}'

# 4) Ingest usage (customer key from step 2)
curl -s -X POST http://127.0.0.1:8000/api/v1/usage/events \
  -H "X-Api-Key: sk_live_..." \
  -H "X-Request-ID: trace-42" \
  -H "Content-Type: application/json" \
  -d '{"meter_code":"api_calls","quantity":"10050","idempotency_key":"evt-1"}'

# 5) Preview and generate invoice (admin)
curl -s http://127.0.0.1:8000/api/v1/customers/1/invoices/preview \
  -H "X-Admin-Key: dev-admin-key-change-me"
curl -s -X POST http://127.0.0.1:8000/api/v1/customers/1/invoices \
  -H "X-Admin-Key: dev-admin-key-change-me"
```

Starter plan includes **10_000** `api_calls`; overage is **1 cent** per call. The preview above bills **50** cents for **10_050** calls.

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/meters` | — | Billable metrics |
| GET | `/api/v1/plans` | — | Plans with included units and overage rates |
| POST | `/api/v1/customers` | Admin | Create customer + one-time `api_key` |
| GET | `/api/v1/customers` | Admin | List customers |
| GET | `/api/v1/customers/{id}` | Admin | One customer |
| POST | `/api/v1/customers/{id}/subscriptions` | Admin | Start subscription |
| GET | `/api/v1/customers/{id}/subscriptions` | Admin | Active subscription |
| POST | `/api/v1/usage/events` | Customer | Idempotent usage ingest |
| GET | `/api/v1/usage/summary` | Customer | Period totals (same as `/me/usage/summary`) |
| GET | `/api/v1/me` | Customer | Resolve API key to account |
| GET | `/api/v1/me/invoices/preview` | Customer | Overage preview |
| GET | `/api/v1/customers/{id}/invoices/preview` | Admin | Same preview |
| POST | `/api/v1/customers/{id}/invoices` | Admin | Persist invoice for period |
| GET | `/api/v1/customers/{id}/invoices` | Admin | Invoice history |
| GET | `/api/v1/health/live` | — | Liveness |
| GET | `/api/v1/health/ready` | — | Database readiness |

## Where the rules live

| Concern | Code |
|---------|------|
| Admin vs customer auth | `app/api/deps.py` |
| Idempotent usage | `UsageService.ingest_event`, DB unique `(customer_id, idempotency_key)` |
| Period totals | `BillingRepository.sum_usage` |
| Overage math | `InvoiceService.preview` — `max(0, usage − included) × unit_price_cents` |
| HTTP docs | Route `summary` / `description` on each endpoint module |

Routes stay thin; services raise `AppError` subclasses; repositories only use `AsyncSession`.

## Setup and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs — the API description at the top walks through the billing flow.

## Tests

```bash
pytest -v
ruff check app tests alembic
```

Tests use in-memory SQLite, auto-create tables, and seed the catalog.

## Postgres

```bash
docker compose up --build
```

Compose runs migrations before uvicorn, same as `scripts/start.sh`.
