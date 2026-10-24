# FastAPI Media Processing

An intermediate FastAPI service: **JWT auth**, user-owned **media assets** (metadata), **processing presets**, and synchronous **jobs** that simulate thumbnail, resize, transcode, and audio-extract pipelines.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). OpenAPI text in `app/main.py` explains ownership and operations.

## What you get

| Area | Behavior |
|------|----------|
| Auth | Register, login, refresh, logout (same pattern as other intermediate samples) |
| Assets | Register metadata; list/get; owner patch/delete |
| Presets | CRUD on named operation + parameters |
| Jobs | Submit with preset or inline operation; simulated output metadata |
| Catalog | Admin-only `GET /jobs/operations` |
| Errors | **401** / **403** / **404** / **409** via `AppError` |

## Operations

| Operation | Allowed kinds | Key parameters |
|-----------|---------------|----------------|
| `thumbnail` | image | `width`, `height` |
| `resize` | image, video | `max_width`, `max_height` |
| `transcode` | video | `format`: `mp4` or `webm` |
| `extract_audio` | video | `format`: `mp3` or `wav` |

## Seed accounts

| Email | Password | Notes |
|-------|----------|--------|
| `admin@example.com` | `AdminPass123!` | Asset `hero-banner.jpg`, preset `1`, job `1` |
| `demo@example.com` | `DemoPass123!` | Video `promo-reel.mp4` |

## Quick start

```bash
cd intermediate/fastapi-media-processing
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

### Submit a thumbnail job (admin)

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=AdminPass123!" | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"asset_id": 1, "preset_id": 1}'
```

Use `/docs` → **Authorize** with a bearer token from login.

## Swagger walkthrough

1. Login as admin → **Authorize**.
2. **GET /jobs/operations** — inspect allowed kinds and parameters.
3. **GET /assets** and **GET /jobs** — seed data.
4. **POST /jobs** — preset or inline transcode example on asset `2` as demo user.
5. **POST /presets** — save a resize preset and reuse it.

## Layout

```
app/
  schemas/media.py
  repositories/media_repository.py
  services/media_service.py
  api/v1/endpoints/assets.py
  api/v1/endpoints/presets.py
  api/v1/endpoints/jobs.py
```

## API reference

| Method | Path | Who | Description |
|--------|------|-----|-------------|
| GET/POST | `/api/v1/assets` | Bearer | List / register metadata |
| GET/PATCH/DELETE | `/api/v1/assets/{id}` | Owner | Asset CRUD |
| GET/POST | `/api/v1/presets` | Bearer | List / create presets |
| GET/PATCH/DELETE | `/api/v1/presets/{id}` | Owner | Preset CRUD |
| GET | `/api/v1/jobs/operations` | Admin | Operations catalog |
| GET/POST | `/api/v1/jobs` | Bearer | List / submit job |
| GET | `/api/v1/jobs/{id}` | Owner | Fetch one job |

Auth routes: `/api/v1/auth/*`, users: `/api/v1/users` (admin list).

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-media-processing .
docker run --rm -p 8000:8000 fastapi-media-processing
```
