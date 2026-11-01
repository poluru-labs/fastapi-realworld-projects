# Policy authorization API

Advanced FastAPI sample combining **RBAC** (roles on users), **policy rules** (allow/deny with
priority), a central **`/policy/evaluate`** decision point, and **ABAC** clearance on documents.

OpenAPI narrative: `app/main.py`. Try `/docs` after seeding.

## Auth

| Mechanism | Used for |
|-----------|----------|
| `Authorization: Bearer` | Users — documents, evaluate |
| `X-Admin-Key` | Policy rules and role assignments |

## Endpoints

| Method | Path |
|--------|------|
| POST | `/api/v1/auth/register`, `/auth/login`, GET `/auth/me` |
| GET/POST | `/api/v1/policy/rules` (admin) |
| POST | `/api/v1/policy/role-assignments` (admin) |
| GET | `/api/v1/policy/roles` (admin) |
| POST | `/api/v1/policy/evaluate` |
| GET/POST | `/api/v1/documents` |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload
```

## Seed users

| Email | Password | Role |
|-------|----------|------|
| `editor@example.com` | `DemoPass123!` | editor |
| `viewer@example.com` | `DemoPass123!` | viewer |

## Evaluate example

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/policy/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"documents:read","resource":"document/1","resource_attributes":{"classification":"internal"}}'
```

## Tests

```bash
pytest -v
ruff check app tests
```
