# FastAPI Polls API

A beginner-friendly FastAPI service for creating polls, casting votes, and reading live totals. It uses versioned routes, Pydantic schemas, repository/service layers, health checks, and interactive OpenAPI docs at `/docs`. Polls are stored in an in-memory mock database (data resets when the process restarts).

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — short JSON pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness for probes and monitoring |
| Polls CRUD | Create, read, update, delete on `/api/v1/polls` |
| Voting | `POST /api/v1/polls/{id}/votes` — increment an option’s vote count |
| Validation | Question length, at least two unique options, non-negative votes |
| Errors | Domain errors return JSON `{"detail": "..."}` with appropriate HTTP status |
| CORS | Configurable origins (defaults allow local frontends on port 3000) |
| Tests | Pytest coverage for list, create, vote, 404, and health |

## Project layout

```
app/
  main.py                 # App factory, OpenAPI metadata, CORS, exception handlers
  core/                   # Settings (pydantic-settings), AppError
  api/v1/endpoints/       # HTTP route handlers (polls, health)
  schemas/                # Pydantic request/response models
  repositories/           # In-memory poll store
  services/               # Business logic
tests/
  api/v1/                 # API integration tests
```

### Request flow (end to end)

```mermaid
flowchart LR
  Client --> Router["API router /api/v1"]
  Router --> Endpoints["endpoints/polls.py"]
  Endpoints --> Service["PollService"]
  Service --> Repo["PollRepository"]
  Repo --> Memory["In-memory dict"]
```

1. **HTTP** — FastAPI matches the path and parses the body into `PollCreate`, `PollUpdate`, or `VoteCreate`.
2. **Dependencies** — `get_poll_service` injects a shared `PollService` (and repository) per request.
3. **Service** — Maps missing polls or options to 404 via `AppError`.
4. **Repository** — Reads/writes the in-memory catalog (seed data: two sample polls).

## Setup

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional environment file:

```bash
cp .env.example .env
```

See `.env.example` for `APP_NAME`, `DEBUG`, `API_V1_PREFIX`, and `CORS_ORIGINS`.

## Run the server

```bash
uvicorn app.main:app --reload
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | API root |
| http://127.0.0.1:8000/docs | Swagger UI (try endpoints in the browser) |
| http://127.0.0.1:8000/redoc | ReDoc |

## End-to-end walkthrough

With the server running, the following exercises the poll lifecycle using `curl`.

**1. Welcome and health**

```bash
curl -s http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/api/v1/health
```

**2. List seed polls**

```bash
curl -s http://127.0.0.1:8000/api/v1/polls
```

**3. Create a poll**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/polls \
  -H "Content-Type: application/json" \
  -d '{"question": "Tabs or spaces?", "options": ["Tabs", "Spaces"]}'
```

**4. Cast a vote**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/polls/1/votes \
  -H "Content-Type: application/json" \
  -d '{"option_id": 1}'
```

**5. Partial update (PATCH)**

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/polls/3 \
  -H "Content-Type: application/json" \
  -d '{"question": "Tabs or spaces (2 spaces)?"}'
```

**6. Delete**

```bash
curl -s -X DELETE http://127.0.0.1:8000/api/v1/polls/3
```

### Same flow in Swagger UI

Open http://127.0.0.1:8000/docs, expand **polls**, and try **POST /api/v1/polls** and **POST /api/v1/polls/{poll_id}/votes**.

### Automated check

```bash
pytest -v
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/polls` | List all polls |
| GET | `/api/v1/polls/{id}` | Get poll by id |
| POST | `/api/v1/polls` | Create poll |
| PUT | `/api/v1/polls/{id}` | Replace poll (full body; resets votes) |
| PATCH | `/api/v1/polls/{id}` | Partial update |
| POST | `/api/v1/polls/{id}/votes` | Cast a vote for an option |
| DELETE | `/api/v1/polls/{id}` | Delete poll |

### Poll JSON shape

**Create / replace body**

```json
{
  "question": "string (1–200 chars)",
  "options": ["Choice A", "Choice B"]
}
```

**Read response** — `id`, `question`, and `options` (each with `id`, `text`, `votes`).

**Vote body**

```json
{
  "option_id": 1
}
```

## Lint

```bash
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-polls-api .
docker run --rm -p 8000:8000 fastapi-polls-api
```

Then use the walkthrough above against `http://127.0.0.1:8000`.
