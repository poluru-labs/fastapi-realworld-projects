# FastAPI Quiz

A beginner FastAPI service for building and taking **multiple-choice quizzes**. Quizzes, questions, and scores live in memory and reset when the process restarts.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). The OpenAPI description in `app/main.py` walks through authoring vs taking a quiz.

## What you get

| Area | Behavior |
|------|----------|
| Quizzes | Draft → published → archived workflow |
| Questions | 2–6 choices, `correct_index`, edit only in draft |
| Play | `/play` hides answers for published quizzes |
| Submit | Score, percentage, per-question feedback |
| Errors | `{"detail": "..."}` with 404 and 409 |

## Quick start

```bash
cd beginner/fastapi-quiz
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

### Try the seed quiz

1. `GET /api/v1/quizzes/1/play` — three questions, no answer key.
2. `POST /api/v1/quizzes/1/submit` with `"choice_index": 1` on each question (all correct in seed data).

## Suggested walkthrough

1. List published quizzes → open id `1` author view to see `correct_index`.
2. Create a draft → add questions → publish.
3. Play and submit from `/docs`.

## Layout

```
app/
  main.py                 # OpenAPI narrative
  schemas/quiz.py         # Pydantic models
  repositories/quiz_repository.py
  services/quiz_service.py
  api/v1/endpoints/       # quizzes, questions, health
tests/api/v1/test_quiz.py
```

## Tests

```bash
pytest -v
ruff check app tests
```
