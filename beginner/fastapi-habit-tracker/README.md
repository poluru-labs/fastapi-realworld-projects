# FastAPI Habit Tracker

A beginner-friendly habit tracker. Routes live under `/api/v1`. Each request goes through an endpoint, a service, and an in-memory repository. Data resets when the process restarts.

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness |
| Habits | CRUD, pause/resume on `/api/v1/habits` |
| Check-ins | Log one completion per day per habit |
| Stats | `GET /api/v1/habits/{id}/stats` — streak and weekly progress |
| Categories | `GET /api/v1/habits/categories` |
| Filters | category, search, paused |
| Docs | Swagger at `/docs` with POST examples |

## Project layout

```
app/
  main.py                 # OpenAPI narrative, CORS, AppError handler
  core/                   # Settings, AppError
  api/v1/endpoints/       # habits, health
  schemas/habit.py        # Pydantic models
  repositories/           # In-memory store
  services/               # Streak math, duplicate-day checks
tests/api/v1/test_habits.py
```

### Request flow

```mermaid
flowchart LR
  Client --> Router["/api/v1"]
  Router --> Endpoints["habits.py"]
  Endpoints --> Service["HabitService"]
  Service --> Repo["HabitRepository"]
```

## Rules

| Field | Rule |
|-------|------|
| `name` | Required, 1–80 chars |
| `category` | Defaults to `General` |
| `target_days_per_week` | 1–7, used by stats |
| `checked_on` | ISO date; one row per habit per day |
| Paused habits | New check-ins return **409** |

## Seed data

| Habit | Category | Target/wk | Notes |
|-------|----------|-----------|-------|
| Morning run | Health | 4 | Check-ins Oct 12–14 (3-day streak) |
| Read 20 minutes | Learning | 7 | One check-in Oct 14 |
| Evening meditation | Health | 5 | **Paused** |

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

**List habits and stats**

```bash
curl -s http://127.0.0.1:8000/api/v1/habits
curl -s "http://127.0.0.1:8000/api/v1/habits/1/stats?week_of=2026-10-14"
```

**Create a habit and log a day**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/habits \
  -H 'Content-Type: application/json' \
  -d '{"name":"Journal","category":"Mindfulness","target_days_per_week":5}'

curl -s -X POST http://127.0.0.1:8000/api/v1/habits/4/check-ins \
  -H 'Content-Type: application/json' \
  -d '{"checked_on":"2026-10-15","note":"Morning pages"}'
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/habits` | List habits |
| GET | `/api/v1/habits/categories` | Categories |
| POST | `/api/v1/habits` | Create |
| PATCH | `/api/v1/habits/{id}` | Update |
| POST | `/api/v1/habits/{id}/pause` | Pause |
| POST | `/api/v1/habits/{id}/resume` | Resume |
| DELETE | `/api/v1/habits/{id}` | Delete habit + check-ins |
| GET | `/api/v1/habits/{id}/check-ins` | List check-ins |
| POST | `/api/v1/habits/{id}/check-ins` | Log check-in |
| DELETE | `/api/v1/habits/{id}/check-ins/{cid}` | Remove check-in |
| GET | `/api/v1/habits/{id}/stats` | Streak and weekly counts |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-habit-tracker .
docker run --rm -p 8000:8000 fastapi-habit-tracker
```
