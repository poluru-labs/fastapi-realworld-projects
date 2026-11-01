# FastAPI Image Metadata

A beginner-friendly FastAPI service for **image uploads**, **Pillow-extracted metadata** (width, height, format), captions, and tags. Images live in memory and reset when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). See `app/main.py` for the OpenAPI walkthrough.

## What you get

| Area | Behavior |
|------|----------|
| Upload | `POST /api/v1/images` — multipart `file`, optional `caption`, comma-separated `tags` |
| Metadata | List, get, patch caption/tags; pixels and format are fixed after upload |
| Download | `GET /api/v1/images/{id}/content` — inline image bytes |
| Formats | JPEG, PNG, WEBP, GIF — other uploads return **400** |
| Limits | `MAX_UPLOAD_BYTES` (default 5 MiB) — **413** when exceeded |
| Filters | `format`, `min_width`, `min_height`, and `q` on filename, caption, or tags |

## Seed data

| Id | Filename | Format | Dimensions |
|----|----------|--------|------------|
| `1` | hero.jpg | JPEG | 1280×720 |
| `2` | icon.png | PNG | 64×64 |

## Setup

```bash
cd beginner/fastapi-image-metadata
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough (curl)

```bash
curl -s http://127.0.0.1:8000/api/v1/images/1 | jq .

curl -s -X POST http://127.0.0.1:8000/api/v1/images \
  -F "file=@./path/to/photo.jpg" \
  -F "caption=Product shot" \
  -F "tags=product,web"

curl -s -o preview.png http://127.0.0.1:8000/api/v1/images/2/content
```

Use `/docs` → **images** → **POST /api/v1/images** to upload from the browser.

## Layout

```
app/
  main.py
  schemas/image.py
  repositories/image_repository.py
  services/image_service.py
  api/v1/endpoints/images.py
tests/api/v1/test_images.py
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/images` | List (query: `format`, `min_width`, `min_height`, `q`) |
| POST | `/api/v1/images` | Multipart upload + metadata extraction |
| GET | `/api/v1/images/{id}` | Metadata |
| GET | `/api/v1/images/{id}/content` | Image bytes |
| PATCH | `/api/v1/images/{id}` | Update caption and/or tags |
| DELETE | `/api/v1/images/{id}` | Delete |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-image-metadata .
docker run --rm -p 8000:8000 fastapi-image-metadata
```
