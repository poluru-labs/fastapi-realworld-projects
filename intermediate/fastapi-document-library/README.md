# FastAPI Document Library

An intermediate FastAPI sample for **folders**, **nested documents**, **publish workflow**, and **revision history** — with JWT auth and a public library index.

OpenAPI walkthrough: `app/main.py`. Try flows in [Swagger UI](/docs).

## What intermediate developers practice

| Topic | Where it shows up |
|-------|-------------------|
| Nested routes | `/folders/{folder_slug}/documents/{doc_slug}` |
| Optional auth | Public reads for published docs; invalid token still **401** |
| Authorization | Drafts return **404** to strangers (not **403**) |
| Explicit workflow | `/publish`, `/unpublish`, `/archive`, `/restore` routes |
| Revisions | Each publish stores an immutable snapshot |
| Discovery | `/library/documents` searches all published content |

## Seed accounts

| Email | Password |
|-------|----------|
| `demo@example.com` | `DemoPass123!` |
| `admin@example.com` | `AdminPass123!` |

Published without login:

- `GET /api/v1/folders/product-docs/documents/getting-started`
- `GET /api/v1/library/documents?q=getting`

Draft (404 unless demo token):

- `GET /api/v1/folders/product-docs/documents/roadmap-draft`

## Setup

```bash
cd intermediate/fastapi-document-library
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough

```bash
curl -s http://127.0.0.1:8000/api/v1/library/documents | jq .

curl -s http://127.0.0.1:8000/api/v1/folders/product-docs/documents/getting-started | jq .

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=demo@example.com&password=DemoPass123!" | jq -r .access_token)

curl -s -X POST \
  http://127.0.0.1:8000/api/v1/folders/product-docs/documents/roadmap-draft/publish \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## API reference (high level)

| Area | Paths |
|------|--------|
| Library | `GET /library/documents`, `GET /library/tags` |
| Folders | `GET/POST /folders`, `GET/PATCH/DELETE /folders/{slug}` |
| Documents | CRUD under `/folders/{slug}/documents/...` |
| Workflow | `POST .../publish`, `.../unpublish`, `.../archive`, `.../restore` |
| History | `GET .../revisions` (author) |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-document-library .
docker run --rm -p 8000:8000 fastapi-document-library
```
