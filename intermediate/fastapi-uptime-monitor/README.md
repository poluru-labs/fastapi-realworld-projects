# FastAPI Uptime Monitor

An intermediate FastAPI sample for **HTTP monitors**, **mock probes**, **check history**, and **public status pages** — with JWT auth and no real outbound requests.

OpenAPI walkthrough: `app/main.py`. Explore in [Swagger UI](/docs).

## Concepts

| Topic | Implementation |
|-------|----------------|
| Monitors | URL + expected status; owned per account |
| Mock probe | Path/host hints: `down`, `slow`, `404` — see `ProbeClient` |
| Manual runs | `POST /monitors/{slug}/checks` (async) |
| Pause | Paused monitors reject new checks with **409** |
| Public status | `GET /status/{slug}` when `is_public=true` |

## Seed (`demo@example.com` / `DemoPass123!`)

| Slug | Simulated status | Public |
|------|------------------|--------|
| `api-gateway` | up | yes |
| `billing-service` | down | no |
| `docs-site` | degraded | yes |

## Setup

```bash
cd intermediate/fastapi-uptime-monitor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough

```bash
curl -s http://127.0.0.1:8000/api/v1/status/api-gateway | jq .

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=demo@example.com&password=DemoPass123!" | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/v1/monitors/api-gateway/checks \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## API reference

| Method | Path | Auth |
|--------|------|------|
| GET/POST | `/api/v1/monitors` | JWT |
| POST | `/monitors/{slug}/checks` | JWT |
| GET | `/monitors/{slug}/checks` | JWT |
| POST | `/monitors/{slug}/pause`, `/resume` | JWT |
| GET | `/api/v1/status/{slug}` | Public (if enabled) |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-uptime-monitor .
docker run --rm -p 8000:8000 fastapi-uptime-monitor
```
