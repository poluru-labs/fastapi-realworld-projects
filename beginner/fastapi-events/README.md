# FastAPI Events

A beginner-friendly FastAPI service for **community events**: schedule sessions, filter listings, **cancel** events, and collect **registrations** with capacity and duplicate-email rules. Data is in memory and resets when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). See `app/main.py` for the OpenAPI walkthrough.

## What you get

| Area | Behavior |
|------|----------|
| Events | Create, list (filters), get with registrations, patch, delete |
| Cancel | `POST .../cancel` — no new sign-ups; **409** if already cancelled |
| Registrations | Register by email; **409** when full, duplicate, or cancelled |
| Validation | `ends_at` must be after `starts_at` (create and patch) |
| Errors | **404** missing ids; **409** business rules |

## Seed data

| Id | Title | Status | Notes |
|----|-------|--------|--------|
| `1` | Python meetup | scheduled | 2 registrations, cap 50 |
| `2` | Cancelled workshop | cancelled | filter with `?status=cancelled` |
| `3` | Open house | scheduled | no attendance cap |

## Setup

```bash
cd beginner/fastapi-events
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough (curl)

```bash
curl -s "http://127.0.0.1:8000/api/v1/events?status=scheduled"

curl -s -X POST http://127.0.0.1:8000/api/v1/events/1/registrations \
  -H "Content-Type: application/json" \
  -d '{"name":"Jordan","email":"jordan@example.com"}'

curl -s -X POST http://127.0.0.1:8000/api/v1/events/1/cancel
```

Use `/docs` for the full flow with **Examples** on create and register.

## Layout

```
app/
  main.py
  schemas/event.py
  repositories/event_repository.py
  services/event_service.py
  api/v1/endpoints/events.py
tests/api/v1/test_events.py
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/events` | List (query: `status`, `starts_after`, `starts_before`, `q`) |
| POST | `/api/v1/events` | Create scheduled event |
| GET | `/api/v1/events/{id}` | Event + registrations |
| PATCH | `/api/v1/events/{id}` | Partial update |
| DELETE | `/api/v1/events/{id}` | Delete event and registrations |
| POST | `/api/v1/events/{id}/cancel` | Cancel event |
| GET | `/api/v1/events/{id}/registrations` | List registrations |
| POST | `/api/v1/events/{id}/registrations` | Register attendee |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-events .
docker run --rm -p 8000:8000 fastapi-events
```
