# FastAPI URL Shortener

A beginner-friendly FastAPI service to **shorten URLs**, **redirect** with click tracking, and **filter** your link catalog. Data is in memory and resets when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). See `app/main.py` for the OpenAPI walkthrough.

## What you get

| Area | Behavior |
|------|----------|
| Links | Create (auto or custom code), list, get, patch, delete |
| Redirect | `GET /api/v1/r/{code}` → **302** and increment clicks |
| Inactive | Deactivated links return **410 Gone** on redirect |
| Validation | `http`/`https` targets; codes are 3–32 alphanumeric/`_`/`-` |
| Errors | **404** missing codes; **409** duplicate vanity codes |

## Seed data

| Code | Title | Active | Clicks |
|------|-------|--------|--------|
| `docs` | FastAPI docs | yes | 12 |
| `github` | GitHub repo | yes | 4 |
| `old-sale` | Expired promo | no | 99 |

## Setup

```bash
cd beginner/fastapi-url-shortener
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough (curl)

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/links \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://example.com","title":"Demo","custom_code":"demo"}'

curl -s -D - -o /dev/null http://127.0.0.1:8000/api/v1/r/demo
```

Use `/docs` for the full flow with **Examples** on create.

## Layout

```
app/
  main.py
  schemas/link.py
  repositories/link_repository.py
  services/link_service.py
  api/v1/endpoints/links.py
  api/v1/endpoints/redirect.py
tests/api/v1/test_links.py
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/links` | List (query: `is_active`, `q`) |
| POST | `/api/v1/links` | Create short link |
| GET | `/api/v1/links/{code}` | Metadata |
| PATCH | `/api/v1/links/{code}` | Update |
| DELETE | `/api/v1/links/{code}` | Delete |
| GET | `/api/v1/r/{code}` | Redirect (302) |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-url-shortener .
docker run --rm -p 8000:8000 fastapi-url-shortener
```
