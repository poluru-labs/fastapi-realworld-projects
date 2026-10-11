# FastAPI Movie Watchlist

A beginner-friendly personal watchlist. Routes live under `/api/v1`. Each request goes through an endpoint, a service, and an in-memory repository. Data resets when the process restarts.

## What you get

| Feature | Details |
|---------|---------|
| Root welcome | `GET /` — short JSON pointer to `/docs` |
| Health | `GET /api/v1/health` — liveness for probes |
| Movies | Create, read, update, pin, mark watched, and delete on `/api/v1/movies` |
| Genres | `GET /api/v1/movies/genres` — distinct genre labels |
| Filters | `genre`, `search`, `status`, and `pinned` on the list |
| Validation | Title/director length, optional year and runtime via Pydantic |
| Uniqueness | Duplicate IMDb ids return **409** (case insensitive when comparing) |
| Errors | Missing movies return `{"detail": "Movie {id} not found"}` with status 404 |
| Docs | Swagger UI at `/docs` and ReDoc at `/redoc`, with request examples |
| Tests | Pytest coverage for seed data, search, IMDb rules, pin, watched, delete, genres |

## Project layout

```
app/
  main.py                 # App factory, CORS, exception handlers, OpenAPI text
  core/                   # Settings (pydantic-settings), AppError types
  api/v1/endpoints/       # HTTP route handlers
  schemas/                # Pydantic request/response models
  repositories/           # In-memory movie store
  services/               # IMDb uniqueness and 404 mapping
tests/
  api/v1/                 # API integration tests
```

### Request flow

```mermaid
flowchart LR
  Client --> Router["API router /api/v1"]
  Router --> Endpoints["endpoints/movies.py"]
  Endpoints --> Service["MovieService"]
  Service --> Repo["MovieRepository"]
  Repo --> Memory["In-memory dict"]
```

1. **HTTP** — FastAPI matches the path and parses the body into `MovieCreate` or `MovieUpdate`.
2. **Dependencies** — `get_movie_service` injects one shared `MovieService` and repository.
3. **Service** — Enforces unique IMDb id and maps a missing id to `NotFoundError`.
4. **Repository** — Reads and writes the in-memory watchlist. Three movies are seeded.

## Rules

| Field | Rule |
|-------|------|
| `title` | Required. 1–200 characters after trim. |
| `director` | Required. 1–120 characters after trim. |
| `imdb_id` | Optional. Unique when set (case insensitive). |
| `genre` | Defaults to `Drama`. At most 60 characters. |
| `release_year` | Optional integer from 1888 through 2100. |
| `runtime_minutes` | Optional integer from 1 through 600. |
| `status` | `want_to_watch` (default), `watching`, or `watched`. |
| `pinned` | Defaults to `false`. Pinned titles sort to the top of the list. |
| id | Integers starting at 1. The next id after the seed data is 4. |

A `PATCH` with an empty body `{}` changes nothing. Send `"imdb_id": ""` to clear an IMDb id.

`search` matches `title`, `director`, or `imdb_id` and ignores case. `genre` is an exact match (case insensitive). You can combine query parameters.

Inside the pinned group and inside the non-pinned group, smaller ids come first.

## Seed data

| id | Title | Status | Notes |
|----|-------|--------|-------|
| 1 | Inception | `watching` | Pinned, IMDb `tt1375666` |
| 2 | The Shawshank Redemption | `want_to_watch` | |
| 3 | Spirited Away | `watched` | No IMDb id |

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

**2. List seed movies (pinned first)**

```bash
curl -s http://127.0.0.1:8000/api/v1/movies
curl -s http://127.0.0.1:8000/api/v1/movies/genres
```

**3. Filter by status**

```bash
curl -s 'http://127.0.0.1:8000/api/v1/movies?status=want_to_watch'
```

**4. Add a movie**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/movies \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Matrix",
    "director": "Lana Wachowski, Lilly Wachowski",
    "imdb_id": "tt0133093",
    "genre": "Science Fiction",
    "release_year": 1999,
    "runtime_minutes": 136
  }'
```

**5. Start watching**

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/movies/4 \
  -H "Content-Type: application/json" \
  -d '{"status": "watching"}'
```

**6. Pin for watch next**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/movies/4/pin
```

**7. Mark watched (shortcut route)**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/movies/4/mark-watched
```

**8. Delete**

```bash
curl -s -X DELETE http://127.0.0.1:8000/api/v1/movies/4
```

Open http://127.0.0.1:8000/docs and expand **movies** to run the same flow without `curl`.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/movies/genres` | Distinct genres |
| GET | `/api/v1/movies` | List movies (query filters) |
| GET | `/api/v1/movies/{id}` | Get one movie |
| POST | `/api/v1/movies` | Create movie |
| PUT | `/api/v1/movies/{id}` | Replace movie |
| PATCH | `/api/v1/movies/{id}` | Partial update |
| POST | `/api/v1/movies/{id}/pin` | Pin (watch next) |
| POST | `/api/v1/movies/{id}/unpin` | Clear pin |
| POST | `/api/v1/movies/{id}/mark-watched` | Set status to watched |
| DELETE | `/api/v1/movies/{id}` | Delete movie |

## Where the rules live

| Rule | Location |
|------|----------|
| Request validation | `app/schemas/movie.py` |
| IMDb uniqueness | `MovieService` + `MovieRepository.imdb_id_taken` |
| List ordering and filters | `MovieRepository.list_movies` |
| HTTP status mapping | `AppError` handler in `app/main.py` |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-movie-watchlist .
docker run --rm -p 8000:8000 fastapi-movie-watchlist
```
