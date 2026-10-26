# FastAPI Webhook Inbox

An intermediate FastAPI service: **JWT auth**, user-owned **webhook endpoints**, public **ingest** with shared secrets, idempotent delivery storage, and an inbox to **acknowledge** events.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). OpenAPI text in `app/main.py` explains ownership and ingest headers.

## What you get

| Area | Behavior |
|------|----------|
| Auth | Register, login, refresh, logout (same pattern as other intermediate samples) |
| Endpoints | Provision slugs; one-time **webhook_token** on create |
| Ingest | `POST /hooks/{slug}/deliveries` with `X-Webhook-Token` + `Idempotency-Key` |
| Inbox | List/filter deliveries; ack pending items |
| Errors | **401** / **403** / **404** / **409** via `AppError` |

## Seed accounts

| Email | Password | Endpoint | Token |
|-------|----------|----------|--------|
| `admin@example.com` | `AdminPass123!` | `billing-stripe` | `seed-webhook-billing-stripe` |
| `demo@example.com` | `DemoPass123!` | `crm-sync` (paused) | `seed-webhook-crm-sync` |

Two seed deliveries exist on `billing-stripe` (one pending, one acked).

## Quick start

```bash
cd intermediate/fastapi-webhook-inbox
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

### Ingest a webhook (no JWT)

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/hooks/billing-stripe/deliveries \
  -H "X-Webhook-Token: seed-webhook-billing-stripe" \
  -H "Idempotency-Key: demo-1" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"invoice.paid","payload":{"id":"inv_1","amount":1200}}'
```

Use `/docs` → login for inbox routes → **Authorize** with bearer token.

## Swagger walkthrough

1. Login as admin → **Authorize**.
2. **GET /endpoints/billing-stripe/deliveries** — seed inbox.
3. **POST /hooks/billing-stripe/deliveries** — ingest headers only.
4. **POST /deliveries/{id}/ack** — mark processed.
5. **POST /endpoints** — provision a new slug and ingest again.

## Layout

```
app/
  schemas/webhook.py
  repositories/webhook_repository.py
  services/endpoint_service.py
  services/delivery_service.py
  api/v1/endpoints/endpoints.py
  api/v1/endpoints/deliveries.py
  api/v1/endpoints/hooks.py
```

## API reference

| Method | Path | Who | Description |
|--------|------|-----|-------------|
| GET/POST | `/api/v1/endpoints` | Bearer | List / provision |
| GET | `/api/v1/endpoints/{slug}/deliveries` | Owner | Endpoint inbox |
| GET/PATCH/DELETE | `/api/v1/endpoints/{slug}` | Owner | Metadata CRUD |
| GET | `/api/v1/deliveries` | Bearer | Inbox (filters) |
| GET | `/api/v1/deliveries/{id}` | Owner | One delivery |
| POST | `/api/v1/deliveries/{id}/ack` | Owner | Acknowledge |
| POST | `/api/v1/hooks/{slug}/deliveries` | Webhook token | Ingest |

Auth routes: `/api/v1/auth/*`, users: `/api/v1/users` (admin list).

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-webhook-inbox .
docker run --rm -p 8000:8000 fastapi-webhook-inbox
```
