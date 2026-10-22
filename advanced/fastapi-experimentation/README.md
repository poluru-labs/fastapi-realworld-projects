# FastAPI Experimentation

An advanced FastAPI service for **A/B experiments**: provision experiments, define **variants** with weights, **start/stop** lifecycle, public **assignments**, idempotent **exposure/conversion** ingest, and admin **results**.

Async SQLAlchemy, Alembic, structured logs, and health probes match the other advanced samples.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

## What you get

| Area | Behavior |
|------|----------|
| Experiments | Admin provision with one-time ingest token |
| Variants | Add while **draft**; weights must sum to 100 to start |
| Lifecycle | `draft` → `running` → `stopped` |
| Assignment | Public GET — stable hash on `subject_id` |
| Events | Token + idempotency; variant must match assignment |
| Results | Exposures, conversions, conversion rate by variant |
| Keys | `X-Admin-Key`, `X-Experiment-Token`, `Idempotency-Key` |

## Quick start

```bash
cd advanced/fastapi-experimentation
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload
```

### Seed experiment

| Key | Ingest token | Status |
|-----|----------------|--------|
| `checkout-button` | `seed-token-checkout-button` | running (50/50 control vs treatment) |

```bash
# Public assignment
curl -s "http://127.0.0.1:8000/api/v1/experiments/checkout-button/assignment?subject_id=user-42"

# Ingest (use variant_key from assignment response)
curl -s -X POST "http://127.0.0.1:8000/api/v1/experiments/checkout-button/events" \
  -H "X-Experiment-Token: seed-token-checkout-button" \
  -H "Idempotency-Key: demo-1" \
  -H "Content-Type: application/json" \
  -d '{"subject_id":"user-42","event_type":"exposure","variant_key":"control","dedupe_key":"u42-e1"}'
```

## Swagger walkthrough

1. **Authorize** with `X-Admin-Key` from `.env`.
2. **GET /experiments/checkout-button/results** — seed metrics.
3. **GET .../assignment** — no auth.
4. **POST .../events** — experiment token headers only.
5. **POST /experiments** — provision a new draft and walk start/stop.

## Layout

```
app/
  core/bucketing.py           # deterministic weighted assignment
  models/experimentation.py
  services/experiment_service.py
  services/event_service.py
  api/v1/endpoints/experiments.py
  api/v1/endpoints/events.py
alembic/versions/001_initial_experimentation.py
```

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET/POST | `/api/v1/experiments` | Admin | List / provision |
| GET | `/api/v1/experiments/{key}` | Admin | Detail + variants |
| POST | `/api/v1/experiments/{key}/variants` | Admin | Add variant (draft) |
| POST | `/api/v1/experiments/{key}/start` | Admin | Start |
| POST | `/api/v1/experiments/{key}/stop` | Admin | Stop |
| GET | `/api/v1/experiments/{key}/assignment` | — | Public assignment |
| GET | `/api/v1/experiments/{key}/results` | Admin | Rolling stats |
| POST | `/api/v1/experiments/{key}/events` | Experiment token | Ingest event |

## Tests and lint

```bash
pytest -v
ruff check app tests alembic
```

Tests bootstrap in-memory SQLite and seed automatically.

## Docker

```bash
docker compose up --build
```
