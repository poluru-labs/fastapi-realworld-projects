# FastAPI Resumable Files

An advanced FastAPI service for **resumable uploads**: admin **sessions**, chunked **parts** with idempotency, client **status** for resume, and **complete** when all bytes are stored. Async SQLAlchemy, Alembic, structured logs, and health probes match the other advanced samples.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

## What you get

| Area | Behavior |
|------|----------|
| Sessions | Admin create with total size and chunk size; one-time **upload_token** |
| Parts | Raw POST body per chunk; **X-Part-Index** + **Idempotency-Key** |
| Resume | `GET .../status` lists missing part indexes and progress |
| Complete | Validates all parts then marks session **completed** |
| Headers | `X-Admin-Key`, `X-Upload-Token`, `Idempotency-Key`, `X-Part-Index` |

## Seed session

| Key | Total | Chunk | Parts done | Token |
|-----|-------|-------|------------|--------|
| `demo-archive` | 1000 B | 250 B | 0–1 (2/4) | `seed-upload-demo-archive` |

## Quick start

```bash
cd advanced/fastapi-resumable-files
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload
```

### Upload remaining parts

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/uploads/demo-archive/parts \
  -H "X-Upload-Token: seed-upload-demo-archive" \
  -H "X-Part-Index: 2" \
  -H "Idempotency-Key: demo-part-2" \
  --data-binary @part2.bin
```

Use `/docs` for admin session routes (authorize with `X-Admin-Key`).

## Swagger walkthrough

1. Authorize admin with `X-Admin-Key`.
2. **GET /uploads/demo-archive/status** with upload token — see missing parts.
3. **POST /uploads/demo-archive/parts** — binary body + part headers.
4. **POST /uploads/demo-archive/complete** — finalize.
5. **POST /uploads** — create a new session.

## Layout

```
app/
  models/uploads.py
  repositories/upload_repository.py
  services/upload_service.py
  api/v1/endpoints/uploads.py
  api/v1/endpoints/parts.py
alembic/versions/001_initial_resumable_files.py
```

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET/POST | `/api/v1/uploads` | Admin | List / create session |
| GET | `/api/v1/uploads/{key}` | Admin | Metadata |
| GET | `/api/v1/uploads/{key}/status` | Upload token | Resume status |
| POST | `/api/v1/uploads/{key}/abort` | Admin | Abort session |
| POST | `/api/v1/uploads/{key}/complete` | Upload token | Finalize |
| POST | `/api/v1/uploads/{key}/parts` | Upload token + idempotency | Upload chunk |

## Tests and lint

```bash
pytest -v
ruff check app tests alembic
```

## Docker

```bash
docker compose up --build
```
