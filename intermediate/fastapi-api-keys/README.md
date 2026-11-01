# FastAPI API Keys

An intermediate FastAPI sample for **minting API keys**, **scope checks**, **peppered hashing**, and **dual authentication** (JWT or `X-Api-Key`).

OpenAPI narrative: `app/main.py`. Try flows in [Swagger UI](/docs).

## Concepts

| Topic | What to learn |
|-------|----------------|
| One-time secret | `POST /keys` returns `secret` once; only `prefix` is stored |
| Hashing | `API_KEY_PEPPER` + SHA-256 — plaintext never persisted |
| Scopes | Keys carry `projects:read`, `projects:write`, `metrics:read` |
| Dual auth | `/access/*` accepts Bearer **or** `X-Api-Key` (key wins if both sent) |
| JWT bypass | Logged-in users skip scope checks on their own account |
| Revoke / rotate | Immediate 401; rotate revokes old key and mints a new secret |

## Seed

| Email | Password |
|-------|----------|
| `demo@example.com` | `DemoPass123!` |

Demo API key (all scopes): see `DEMO_SEED_API_KEY` in `app/repositories/key_repository.py`
and the OpenAPI description.

## Setup

```bash
cd intermediate/fastapi-api-keys
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough

```bash
curl -s http://127.0.0.1:8000/api/v1/access/whoami \
  -H "X-Api-Key: sk_live_demo_seed_key_for_tests_only_32" | jq .

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=demo@example.com&password=DemoPass123!" | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/v1/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"CI","scopes":["projects:read"]}' | jq .
```

## API reference

| Method | Path | Auth |
|--------|------|------|
| GET/POST | `/api/v1/keys` | JWT |
| POST | `/api/v1/keys/{id}/revoke`, `/rotate` | JWT |
| GET | `/api/v1/access/whoami` | JWT or API key |
| GET/POST | `/api/v1/access/projects` | JWT or scoped key |
| GET | `/api/v1/access/metrics` | JWT or `metrics:read` |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-api-keys .
docker run --rm -p 8000:8000 fastapi-api-keys
```
