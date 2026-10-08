# Mock CRUD API

FastAPI service with an industry-standard layout: versioned routes, settings, schemas, repository/service layers, and tests. Data is mock in-memory JSON (resets on restart).

## Project layout

```
app/
  main.py                 # App factory + middleware
  core/                   # Settings, domain errors
  api/v1/endpoints/       # HTTP handlers
  schemas/                # Pydantic request/response models
  repositories/           # Mock data store
  services/               # Business logic
tests/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy environment defaults (optional):

```bash
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

- API root: http://127.0.0.1:8000
- OpenAPI: http://127.0.0.1:8000/docs
- Items CRUD: `/api/v1/items`
- Health: `/api/v1/health`

## Test & lint

```bash
pytest
ruff check app tests
```

## Docker

```bash
docker build -t mock-crud-api .
docker run --rm -p 8000:8000 mock-crud-api
```

## API quick reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/items` | List items |
| GET | `/api/v1/items/{id}` | Get item |
| POST | `/api/v1/items` | Create |
| PUT | `/api/v1/items/{id}` | Replace |
| PATCH | `/api/v1/items/{id}` | Partial update |
| DELETE | `/api/v1/items/{id}` | Delete |
