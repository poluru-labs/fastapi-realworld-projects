# FastAPI Todo

A beginner-friendly todo list. Routes are versioned under `/api/v1`. Each request goes through an endpoint, a service, and an in-memory repository. Data resets when the process restarts.

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — short JSON pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness for probes |
| Todo list | Create, read, update, complete, reopen, and delete on `/api/v1/todos` |
| Filters | `completed` and `priority` query parameters on the list |
| Validation | Title length, notes length, and priority enum via Pydantic |
| Errors | Missing todos return `{"detail": "Todo {id} not found"}` with status 404 |
| Docs | Swagger UI at `/docs` and ReDoc at `/redoc`, with request examples |
| Tests | Pytest coverage for seed data, filters, create, patch, complete, delete, and 422 |

## Project layout

```
app/
  main.py                 # App factory, CORS, exception handlers, OpenAPI text
  core/                   # Settings (pydantic-settings), AppError
  api/v1/endpoints/       # HTTP route handlers
  schemas/                # Pydantic request/response models
  repositories/           # In-memory todo store
  services/               # Looks up missing todos and raises 404
tests/
  api/v1/                 # API integration tests
```

### Request flow

```mermaid
flowchart LR
  Client --> Router["API router /api/v1"]
  Router --> Endpoints["endpoints/todos.py"]
  Endpoints --> Service["TodoService"]
  Service --> Repo["TodoRepository"]
  Repo --> Memory["In-memory dict"]
```

1. **HTTP** — FastAPI matches the path and parses the body into `TodoCreate` or `TodoUpdate`.
2. **Dependencies** — `get_todo_service` injects one shared `TodoService` and repository.
3. **Service** — Maps a missing id to `NotFoundError`, which the app turns into JSON.
4. **Repository** — Reads and writes the in-memory list. Three tasks are seeded.

## Rules

| Field | Rule |
|-------|------|
| `title` | Required. 1–120 characters after leading and trailing spaces are removed. |
| `notes` | Optional. At most 500 characters. Spaces are trimmed. Blank is allowed. |
| `priority` | `low`, `medium`, or `high`. New tasks default to `medium`. |
| `completed` | Defaults to `false`. |
| id | Integers starting at 1. The next id after the seed data is 4. |

Completing a task that is already done, or reopening one that is already open, returns the same todo. It does not fail.

A `PATCH` with an empty body `{}` changes nothing and returns the current todo. Fields you omit stay as they were.

The list is sorted by id. `completed=false` keeps open tasks. `priority=high` keeps one urgency. You can send both.

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

**1. Welcome and health**

```bash
curl -s http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/api/v1/health
```

Expected health body: `{"status":"ok"}`.

**2. List the seed tasks**

```bash
curl -s http://127.0.0.1:8000/api/v1/todos
```

| id | title | priority | completed |
|----|-------|----------|-----------|
| 1 | Buy groceries | medium | false |
| 2 | Read the FastAPI tutorial | high | false |
| 3 | Set up the project | low | true |

**3. Filter**

```bash
curl -s "http://127.0.0.1:8000/api/v1/todos?completed=false"
curl -s "http://127.0.0.1:8000/api/v1/todos?priority=high"
```

**4. Create**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Write the README", "notes": "Include a curl walkthrough"}'
```

Returns `201`. On a fresh server the new id is `4`, priority is `medium`, and completed is `false`.

**5. Partial update**

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/todos/4 \
  -H "Content-Type: application/json" \
  -d '{"priority": "high"}'
```

**6. Complete and reopen**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/todos/4/complete
curl -s -X POST http://127.0.0.1:8000/api/v1/todos/4/reopen
```

**7. Delete**

```bash
curl -s -X DELETE http://127.0.0.1:8000/api/v1/todos/4
```

The body includes `deleted: true` and a snapshot of the removed todo.

**8. Not found**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/todos/999
```

Expect `404` with `{"detail":"Todo 999 not found"}`.

### Same flow in Swagger UI

Open http://127.0.0.1:8000/docs, expand **todos**, and run **POST /api/v1/todos** using the “New open task” example, then **GET /api/v1/todos**.

### Automated check

```bash
pytest -v
ruff check app tests
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/todos` | List todos. Optional `completed` and `priority` |
| GET | `/api/v1/todos/{id}` | Get one todo |
| POST | `/api/v1/todos` | Create a todo (`201`) |
| PATCH | `/api/v1/todos/{id}` | Change only the fields you send |
| POST | `/api/v1/todos/{id}/complete` | Set `completed` to true |
| POST | `/api/v1/todos/{id}/reopen` | Set `completed` to false |
| DELETE | `/api/v1/todos/{id}` | Delete and return a snapshot |

### Create body

```json
{
  "title": "string, 1–120 characters",
  "notes": "optional, up to 500 characters",
  "priority": "low | medium | high",
  "completed": false
}
```

### Read response

```json
{
  "id": 1,
  "title": "Buy groceries",
  "notes": "Milk and bread",
  "priority": "medium",
  "completed": false
}
```

### Patch body

Any subset of `title`, `notes`, `priority`, and `completed`.

## Docker

```bash
docker build -t fastapi-todo .
docker run --rm -p 8000:8000 fastapi-todo
```

Then use the walkthrough against `http://127.0.0.1:8000`.
