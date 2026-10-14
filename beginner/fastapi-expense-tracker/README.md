# FastAPI Expense Tracker

A beginner-friendly personal expense ledger. Routes live under `/api/v1`. Each request goes through an endpoint, a service, and an in-memory repository. Data resets when the process restarts.

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness |
| Expenses | CRUD, flag/unflag, list filters on `/api/v1/expenses` |
| Summary | `GET /api/v1/expenses/summary` — totals and per-category breakdown |
| Categories | `GET /api/v1/expenses/categories` — distinct labels |
| Filters | category, search, flagged, payment_method, date range, amount |
| Amounts | Stored as **cents** (integer) to avoid floating-point rounding |
| Uniqueness | Duplicate `receipt_ref` values return **409** |
| Docs | Swagger at `/docs` with POST examples |

## Project layout

```
app/
  main.py                 # OpenAPI narrative, CORS, AppError handler
  core/                   # Settings, AppError
  api/v1/endpoints/       # expenses, health
  schemas/expense.py      # Pydantic models
  repositories/           # In-memory store
  services/               # Summary math, receipt uniqueness
tests/api/v1/test_expenses.py
```

### Request flow

```mermaid
flowchart LR
  Client --> Router["/api/v1"]
  Router --> Endpoints["expenses.py"]
  Endpoints --> Service["ExpenseService"]
  Service --> Repo["ExpenseRepository"]
```

## Rules

| Field | Rule |
|-------|------|
| `merchant` | Required, 1–120 chars |
| `amount_cents` | Required, positive integer |
| `category` | Defaults to `General` |
| `spent_on` | ISO date `YYYY-MM-DD` |
| `payment_method` | `card`, `cash`, or `transfer` |
| `receipt_ref` | Optional, unique when set |
| `flagged` | Defaults to false; flagged rows sort first |

## Seed data

| Merchant | Category | Amount | Notes |
|----------|----------|--------|-------|
| Corner Coffee | Food | $4.50 | receipt RCPT-1001 |
| Metro Transit | Transport | $85.00 | |
| Cloud Tools | Software | $12.00 | flagged for review |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs

## Walkthrough

```bash
curl -s http://127.0.0.1:8000/api/v1/expenses
curl -s 'http://127.0.0.1:8000/api/v1/expenses/summary?from_date=2026-10-01&to_date=2026-10-31'

curl -s -X POST http://127.0.0.1:8000/api/v1/expenses \
  -H "Content-Type: application/json" \
  -d '{
    "merchant": "Grocery Co-op",
    "amount_cents": 4321,
    "category": "Food",
    "spent_on": "2026-10-12",
    "payment_method": "card"
  }'
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/expenses/categories` | Category list |
| GET | `/api/v1/expenses/summary` | Totals (optional date/category filters) |
| GET | `/api/v1/expenses` | List expenses |
| GET | `/api/v1/expenses/{id}` | One expense |
| POST | `/api/v1/expenses` | Create |
| PUT | `/api/v1/expenses/{id}` | Replace |
| PATCH | `/api/v1/expenses/{id}` | Partial update |
| POST | `/api/v1/expenses/{id}/flag` | Flag for review |
| POST | `/api/v1/expenses/{id}/unflag` | Clear flag |
| DELETE | `/api/v1/expenses/{id}` | Delete |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-expense-tracker .
docker run --rm -p 8000:8000 fastapi-expense-tracker
```
