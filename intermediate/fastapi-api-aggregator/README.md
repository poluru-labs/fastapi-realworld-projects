# FastAPI API Aggregator

An intermediate FastAPI sample that combines **JWT auth**, **owned upstream sources**, **aggregate plans**, and **parallel mock fetches** — without calling real third-party APIs.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). The long-form OpenAPI narrative lives in `app/main.py`.

## Concepts for intermediate developers

| Layer | What to study |
|-------|----------------|
| **Sources** | Register mock upstreams (`mock_catalog` + documented `base_url`). Pause with `is_active`. |
| **Aggregates** | Declarative fan-out: each fragment has a `key`, `source_slug`, and GET `path`. |
| **Runs** | `asyncio.gather` in the service layer; partial failures surface per fragment. |
| **AuthZ** | Other users' slugs return **404** (not **403**) so hidden resources stay indistinguishable. |
| **Idempotency** | Optional `Idempotency-Key` on runs replays the stored result for the same user + slug. |

## Seed accounts

| Email | Password | Notes |
|-------|----------|-------|
| `demo@example.com` | `DemoPass123!` | Owns `users-svc`, `orders-svc`, published `customer-360` |
| `admin@example.com` | `AdminPass123!` | Lists all users, sources, and aggregates |

## Setup

```bash
cd intermediate/fastapi-api-aggregator
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough

```bash
# 1. Login (OAuth2 form — username field holds the email)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=demo@example.com&password=DemoPass123!" | jq -r .access_token)

# 2. Execute the seeded aggregate
curl -s -X POST http://127.0.0.1:8000/api/v1/aggregates/customer-360/runs \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. Idempotent replay
curl -s -X POST http://127.0.0.1:8000/api/v1/aggregates/customer-360/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: demo-run-1" | jq .
```

In Swagger: **Authorize** with the access token, then try **aggregates → POST /runs**.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | OAuth2 password form → tokens |
| GET | `/api/v1/sources` | List mock upstreams (JWT) |
| POST | `/api/v1/sources` | Register upstream |
| GET/PATCH/DELETE | `/api/v1/sources/{slug}` | Read, pause, delete |
| GET/POST | `/api/v1/aggregates` | List / define plan |
| POST | `/api/v1/aggregates/{slug}/publish` | Enable runs |
| POST | `/api/v1/aggregates/{slug}/runs` | Parallel fan-out |
| GET | `/api/v1/aggregates/{slug}/runs` | Run history |

## Layout

```
app/
  services/upstream_client.py   # mock HTTP
  services/aggregate_service.py # gather + idempotency
  repositories/aggregator_repository.py
  api/v1/endpoints/sources.py
  api/v1/endpoints/aggregates.py
tests/api/v1/test_aggregates.py
```

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-api-aggregator .
docker run --rm -p 8000:8000 fastapi-api-aggregator
```
