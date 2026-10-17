# FastAPI Journal

A beginner-friendly personal journal API. Routes live under `/api/v1`. Each request goes through an endpoint, a service, and an in-memory repository. Data resets when the process restarts.

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness |
| Entries | CRUD on `/api/v1/entries` |
| By date | `GET /api/v1/entries/by-date/{YYYY-MM-DD}` |
| Tags | `GET /api/v1/entries/tags` |
| Star | `POST .../star`, `POST .../unstar` |
| Filters | tag, mood, search, starred, date range |
| Docs | Swagger at `/docs` with POST examples |

## Project layout

```
app/
  main.py                 # OpenAPI narrative, CORS, AppError handler
  core/                   # Settings, AppError
  api/v1/endpoints/       # entries, health
  schemas/entry.py        # Pydantic models
  repositories/           # In-memory store
  services/               # One-entry-per-day rule
tests/api/v1/test_entries.py
```

## Rules

| Field | Rule |
|-------|------|
| `entry_date` | Required; unique per entry (**409** on duplicate) |
| `body` | Required, 1–10,000 characters |
| `mood` | Optional: `great`, `good`, `okay`, `low`, `rough` |
| `tags` | Lowercased, deduplicated, max 12 |
| List order | Starred first, then newest date |

## Seed data

| Date | Title | Mood | Starred |
|------|-------|------|---------|
| 2026-10-14 | Shipped the habit tracker | great | yes |
| 2026-10-15 | Reading day | okay | no |

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
curl -s http://127.0.0.1:8000/api/v1/entries | jq
curl -s http://127.0.0.1:8000/api/v1/entries/by-date/2026-10-14 | jq

curl -s -X POST http://127.0.0.1:8000/api/v1/entries \
  -H "Content-Type: application/json" \
  -d '{"entry_date":"2026-10-16","body":"Quiet evening.","mood":"good","tags":["rest"]}' | jq
```

## Tests

```bash
pytest -v
ruff check app tests
```
