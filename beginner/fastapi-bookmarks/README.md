# FastAPI Bookmarks

A beginner-friendly bookmarks API. Routes live under `/api/v1`. Each request goes through an endpoint, a service, and an in-memory repository. Data resets when the process restarts.

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness |
| Bookmarks | CRUD on `/api/v1/bookmarks` |
| Tags | `GET /api/v1/bookmarks/tags` |
| Pin / unpin | `POST .../pin`, `POST .../unpin` |
| Archive | `POST .../archive`, `POST .../unarchive` |
| Filters | tag, search, pinned, archived |
| Docs | Swagger at `/docs` with POST examples |

## Project layout

```
app/
  main.py                 # OpenAPI narrative, CORS, AppError handler
  core/                   # Settings, AppError
  api/v1/endpoints/       # bookmarks, health
  schemas/bookmark.py     # Pydantic models
  repositories/           # In-memory store
  services/               # Thin orchestration
tests/api/v1/test_bookmarks.py
```

### Request flow

```mermaid
flowchart LR
  Client --> Router["/api/v1"]
  Router --> Endpoints["bookmarks.py"]
  Endpoints --> Service["BookmarkService"]
  Service --> Repo["BookmarkRepository"]
```

## Rules

| Field | Rule |
|-------|------|
| `title` | Required, 1–120 chars |
| `url` | Valid http/https URL; unique after normalization |
| `tags` | Lowercased, deduplicated, max 12 |
| `note` | Optional, up to 500 chars |
| List order | Pinned first, then title (A–Z) |
| Archived | Hidden unless `archived=true` on list |

## Seed data

| Title | URL | Tags | Pinned |
|-------|-----|------|--------|
| FastAPI documentation | https://fastapi.tiangolo.com/ | python, docs, api | yes |
| Python tutorial | https://docs.python.org/3/tutorial/ | python, learning | no |

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

**List and filter**

```bash
curl -s http://127.0.0.1:8000/api/v1/bookmarks | jq
curl -s "http://127.0.0.1:8000/api/v1/bookmarks?tag=python" | jq
curl -s http://127.0.0.1:8000/api/v1/bookmarks/tags | jq
```

**Create a bookmark**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bookmarks \
  -H "Content-Type: application/json" \
  -d '{"title":"Pydantic","url":"https://docs.pydantic.dev/latest/","tags":["python"]}' | jq
```

**Pin and archive**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/bookmarks/2/pin | jq
curl -s -X POST http://127.0.0.1:8000/api/v1/bookmarks/2/archive | jq
curl -s "http://127.0.0.1:8000/api/v1/bookmarks?archived=true" | jq
```

## Tests

```bash
pytest -v
ruff check app tests
```
