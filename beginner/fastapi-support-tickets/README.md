# FastAPI Support Tickets

A beginner-friendly FastAPI service for **customer support tickets**: create and filter tickets, add **comments** (including internal notes), and move tickets through **resolve**, **close**, and **reopen**. Data is in memory and resets when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). See `app/main.py` for the OpenAPI walkthrough.

## What you get

| Area | Behavior |
|------|----------|
| Tickets | Create, list (filters), get with comments, patch, delete |
| Comments | Add public or internal notes; **409** on closed tickets |
| Lifecycle | `POST .../resolve`, `/close`, `/reopen` with conflict rules |
| Validation | Email on requester; subject and body length limits |
| Errors | **404** missing ids; **409** business rules |

## Seed data

| Id | Subject | Status | Notes |
|----|---------|--------|--------|
| `1` | Login page returns 500 | open | 2 comments (1 internal) |
| `2` | Invoice total looks wrong | in_progress | assigned to Jordan Lee |
| `3` | Typo on pricing page | closed | use reopen flow in tests |

## Setup

```bash
cd beginner/fastapi-support-tickets
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Walkthrough (curl)

```bash
curl -s "http://127.0.0.1:8000/api/v1/tickets?status=open"

curl -s -X POST http://127.0.0.1:8000/api/v1/tickets/1/comments \
  -H "Content-Type: application/json" \
  -d '{"author_name":"Alex","body":"Still failing on Safari.","is_internal":false}'

curl -s -X POST http://127.0.0.1:8000/api/v1/tickets/1/resolve
```

Use `/docs` for the full flow with **Examples** on create and comment.

## Layout

```
app/
  main.py
  schemas/ticket.py
  repositories/ticket_repository.py
  services/ticket_service.py
  api/v1/endpoints/tickets.py
tests/api/v1/test_tickets.py
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/tickets` | List (query: `status`, `priority`, `q`) |
| POST | `/api/v1/tickets` | Create ticket |
| GET | `/api/v1/tickets/{id}` | Ticket + comments |
| PATCH | `/api/v1/tickets/{id}` | Partial update |
| DELETE | `/api/v1/tickets/{id}` | Delete ticket and comments |
| GET | `/api/v1/tickets/{id}/comments` | List comments |
| POST | `/api/v1/tickets/{id}/comments` | Add comment |
| POST | `/api/v1/tickets/{id}/resolve` | Mark resolved |
| POST | `/api/v1/tickets/{id}/close` | Close ticket |
| POST | `/api/v1/tickets/{id}/reopen` | Reopen ticket |

## Tests and lint

```bash
pytest -v
ruff check app tests
```

## Docker

```bash
docker build -t fastapi-support-tickets .
docker run --rm -p 8000:8000 fastapi-support-tickets
```
