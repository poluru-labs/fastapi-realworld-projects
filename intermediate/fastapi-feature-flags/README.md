# FastAPI Feature Flags

An intermediate FastAPI sample for **flag definitions**, **percentage rollouts**, **allowlists**, and **runtime evaluation** from backend apps.

OpenAPI walkthrough: `app/main.py`. Use [Swagger UI](/docs) — try **runtime → evaluate** with `X-Runtime-Token`.

## Concepts

| Topic | Implementation |
|-------|----------------|
| Management | JWT CRUD on `/api/v1/flags` |
| Targeting | `enabled`, `rollout_percentage`, `allowlist_user_ids` |
| Deterministic rollout | Stable bucket from `sha256(flag_key:user_id)` |
| Runtime | `POST /runtime/evaluate` + `X-Runtime-Token` |
| Reasons | Each evaluation returns `enabled` and a `reason` string |

## Seed

| Email | Password |
|-------|----------|
| `demo@example.com` | `DemoPass123!` |

Runtime token: `seed-runtime-token-demo` (see `flag_repository.py`).

## Setup

```bash
cd intermediate/fastapi-feature-flags
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/runtime/evaluate \
  -H "X-Runtime-Token: seed-runtime-token-demo" \
  -H "Content-Type: application/json" \
  -d '{"flag_keys":["dark-mode","new-checkout"],"context":{"user_id":"u_vip_1"}}' | jq .
```

## API reference

| Method | Path | Auth |
|--------|------|------|
| GET/POST | `/api/v1/flags` | JWT |
| PATCH/DELETE | `/api/v1/flags/{key}` | JWT |
| POST | `/api/v1/runtime/evaluate` | `X-Runtime-Token` |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-feature-flags .
docker run --rm -p 8000:8000 fastapi-feature-flags
```
