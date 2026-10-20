# FastAPI Gradebook

A beginner-friendly FastAPI service: students, courses, enrollments, draft/final grades, and simple reports. Everything is stored in memory (data resets when the process restarts).

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc).

## What you get

| Feature | Details |
|---------|---------|
| Students | CRUD, unique `student_number`, `GET .../report` (final grades only) |
| Courses | CRUD, unique `course_code`, enrollments |
| Grades | Create on a course, list with filters, **percentage** on responses |
| Workflow | New grades are **draft** → **finalize** → **reopen** |
| Defaults | Grade list hides drafts unless `include_draft=true` or `status=draft` |
| Errors | **409** duplicate roster/course codes or enrollments; **404** missing ids |

## Seed data

| Students | Courses |
|----------|---------|
| `STU-001` Alice Nguyen | `CS101` Intro to Programming |
| `STU-002` Bob Patel | `MATH200` Calculus II |

Alice has two **final** grades in CS101; Bob has a **draft** in CS101.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/v1/students` | List / create |
| GET | `/api/v1/students/{id}/report` | Average of final grade % |
| GET/POST/PATCH/DELETE | `/api/v1/students/{id}` | Read / update / delete |
| GET/POST | `/api/v1/courses` | List / create |
| GET/POST | `/api/v1/courses/{id}/enrollments` | Roster |
| POST | `/api/v1/courses/{id}/grades` | Create draft grade |
| GET | `/api/v1/grades` | Filter list |
| PATCH | `/api/v1/grades/{id}` | Update draft |
| POST | `/api/v1/grades/{id}/finalize` | Publish grade |
| POST | `/api/v1/grades/{id}/reopen` | Back to draft |

## Tests and lint

```bash
pytest -v
ruff check app tests
```
