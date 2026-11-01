# FastAPI File Upload

A beginner-friendly FastAPI service for **multipart uploads**, **metadata**, and **downloads**. Files are kept in memory and reset when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). See `app/main.py` for the OpenAPI walkthrough.

## What you get

| Area | Behavior |
|------|----------|
| Upload | `POST /api/v1/files` — form fields `file` + optional `description` |
| Download | `GET /api/v1/files/{id}/content` — bytes with `Content-Disposition` |
| Metadata | List, get, patch description, delete |
| Limits | `MAX_UPLOAD_BYTES` (default 5 MiB) — **413** when exceeded |
| Filters | `content_type` substring and `q` on filename/description |

## Seed data

| Id | Filename | Type |
|----|----------|------|
| `1` | welcome.txt | text/plain |
| `2` | notes.md | text/markdown |

## Setup

```bash
cd beginner/fastapi-file-upload
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough (curl)

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/files \
  -F "file=@./README.md" \
  -F "description=Project readme"

curl -s -O -J http://127.0.0.1:8000/api/v1/files/1/content
```

Use `/docs` → **files** → **POST /api/v1/files** to try multipart upload in the browser.

## Layout

```
app/
  main.py
  schemas/file.py
  repositories/file_repository.py
  services/file_service.py
  api/v1/endpoints/files.py
tests/api/v1/test_files.py
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/files` | List (query: `content_type`, `q`) |
| POST | `/api/v1/files` | Multipart upload |
| GET | `/api/v1/files/{id}` | Metadata |
| GET | `/api/v1/files/{id}/content` | Download |
| PATCH | `/api/v1/files/{id}` | Update description |
| DELETE | `/api/v1/files/{id}` | Delete |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-file-upload .
docker run --rm -p 8000:8000 fastapi-file-upload
```
