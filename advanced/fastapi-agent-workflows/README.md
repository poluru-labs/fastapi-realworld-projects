# Agent workflows API

Advanced FastAPI sample for **agent-shaped orchestration**: ordered **agent** (prompt) and **tool**
steps, admin **publish** workflow, **runner** execution with **idempotency**, and persisted **step
logs**. OpenAPI narratives are in `app/main.py`.

Distinct from [`fastapi-workflow-engine`](../fastapi-workflow-engine) (FSM transitions). This
project models LLM agent pipelines and mock tools.

## Headers

| Header | Role |
|--------|------|
| `X-Admin-Key` | Definitions CRUD, publish, list runs |
| `X-Runner-Key` | Start runs |
| `Idempotency-Key` | Required on `POST /agent-runs` |

## Endpoints

| Method | Path |
|--------|------|
| GET/POST | `/api/v1/agent-workflows` |
| GET/PATCH | `/api/v1/agent-workflows/{slug}` |
| POST | `/api/v1/agent-workflows/{slug}/publish` |
| POST | `/api/v1/agent-runs` |
| GET | `/api/v1/agent-runs` (admin) |
| GET | `/api/v1/agent-runs/{id}` |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m scripts.seed_data
uvicorn app.main:app --reload
```

## Example run

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/agent-runs \
  -H "Content-Type: application/json" \
  -H "X-Runner-Key: dev-runner-key-change-me" \
  -H "Idempotency-Key: demo-1" \
  -d '{"workflow_slug":"research-assistant","input":{"goal":"hybrid search"}}'
```

## Tests

```bash
pytest -v
ruff check app tests
```
