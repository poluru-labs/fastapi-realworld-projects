# Multitenant RAG API

Advanced FastAPI sample: **JWT auth**, **`X-Tenant-Slug` isolation**, knowledge **collections**,
text **ingest** with chunking + demo embeddings, and **cosine retrieval** with citations.

OpenAPI narratives live in `app/main.py`. Use `/docs` to authorize bearer tokens and try queries.

> Embeddings are deterministic hashes for teaching — not OpenAI/Cohere quality. Replace
> `app/core/text_embeddings.py` and add pgvector or a hosted index for production.

## Headers

| Header | Purpose |
|--------|---------|
| `Authorization: Bearer …` | User JWT from `/auth/login` or `/auth/register` |
| `X-Tenant-Slug` | Tenant partition for all `/collections` routes |

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/v1/auth/register` | User + tenant + owner membership |
| POST | `/api/v1/auth/login` | Access token |
| GET | `/api/v1/tenants/mine` | Pick a slug |
| GET/POST | `/api/v1/collections` | List / create (tenant scoped) |
| GET | `/api/v1/collections/{slug}` | Metadata |
| POST | `/api/v1/collections/{slug}/documents` | Ingest plain text |
| GET | `/api/v1/collections/{slug}/documents` | List documents |
| POST | `/api/v1/collections/{slug}/query` | RAG retrieval + stitched answer |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload
```

## Walkthrough

1. Login as seed user:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"DemoPass123!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

2. Query seeded refund policy:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/collections/product-docs/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Slug: acme-corp" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the refund window?","top_k":3}'
```

3. Ingest your own doc, then query again with the same headers.

## Tests

```bash
pytest -v
ruff check app tests
```
