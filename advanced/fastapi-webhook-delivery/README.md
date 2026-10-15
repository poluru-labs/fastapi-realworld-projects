# FastAPI Webhook Delivery

An advanced FastAPI service: async SQLAlchemy, Alembic, JWT auth, **webhook endpoint** registration,
**signed outbound HTTP** delivery, per-attempt history, **Idempotency-Key** on publish/retry, and a
built-in **capture sink** for local development.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

## What you get

| Area | Behavior |
|------|----------|
| Infra | Request id middleware, structured logs, liveness/readiness probes |
| Endpoints | Register subscriber URLs, signing secrets (shown once), `event_types` filters |
| Publish | `POST /webhook-events` stores the event and POSTs to every matching enabled endpoint |
| Signatures | HMAC-SHA256 over `{timestamp}.{body}` in `X-Webhook-Signature` |
| History | `GET .../deliveries` lists attempts with HTTP status, duration, errors |
| Idempotency | Duplicate **Idempotency-Key** on publish returns the same event (no double fan-out) |
| Retry | `POST /webhook-deliveries/{id}/retry` creates a new attempt row |
| Privacy | Another user's event/endpoint id returns **404**, not **403** |
| Dev sink | `POST /api/v1/dev/capture` accepts webhook POSTs in memory |

## Signing (verify on your server)

```python
import hmac, hashlib

def verify(secret: str, timestamp: str, body: bytes, signature_hex: str) -> bool:
    msg = timestamp.encode() + b"." + body
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)
```

Headers on each delivery:

| Header | Purpose |
|--------|---------|
| `X-Webhook-Id` | Event id |
| `X-Webhook-Event` | Event type string |
| `X-Webhook-Timestamp` | Unix seconds when signed |
| `X-Webhook-Signature` | `sha256=<hex>` |

## Project layout

```
app/
  core/webhook_signing.py     # HMAC helpers
  models/webhook.py           # endpoints, events, deliveries
  services/delivery_service.py
  api/v1/endpoints/           # auth, endpoints, events, deliveries, capture
alembic/versions/001_initial_webhook_delivery.py
tests/api/v1/test_webhook_flow.py
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

Seed admin: `admin@example.com` / `AdminPass123!`

**Quick demo**

1. Register and create an endpoint with URL `http://127.0.0.1:8000/api/v1/dev/capture`
2. Save the `signing_secret` from the response
3. Publish an event with `Idempotency-Key`
4. Inspect deliveries on the event id

## API reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/webhook-endpoints` | Register endpoint (secret shown once) |
| GET | `/api/v1/webhook-endpoints` | List your endpoints |
| PATCH | `/api/v1/webhook-endpoints/{id}` | Update URL, filters, enabled |
| POST | `/api/v1/webhook-events` | Publish + deliver (Idempotency-Key) |
| GET | `/api/v1/webhook-events/{id}/deliveries` | Attempt log |
| POST | `/api/v1/webhook-deliveries/{id}/retry` | Retry failed attempt |
| POST | `/api/v1/dev/capture` | Demo subscriber |

## Tests and lint

```bash
pytest -v
ruff check app tests alembic
```

Tests use `httpx` `ASGITransport` so deliveries loop back into the same app (`http://testserver/...`).

## What this demo is not

There is no background worker queue, exponential backoff scheduler, or dead-letter topic. Production
systems persist an outbox and relay with retries — the **delivery service** here is where that logic
would grow without changing the HTTP contract.
