from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

API_DESCRIPTION = """
A simple **flashcard** API for learning FastAPI. Decks and cards live in memory and reset on
restart.

Interactive docs: [Swagger UI](/docs) and [ReDoc](/redoc). Create bodies include **Examples**.

### Build content
1. `POST /api/v1/decks` — create a deck.
2. `POST /api/v1/decks/{id}/cards` — add **front**, **back**, optional **hint**.
3. `GET /api/v1/decks/{id}` — authoring view with every answer visible.

### Study flow
1. `GET /api/v1/decks/{id}/study` — **front** side only (no `back` field).
2. `GET /api/v1/cards/{id}` — flip / reveal the full card after the learner guesses.

### Rules
- Deleting a deck removes its cards.
- Card **position** is reassigned when a card is deleted.
- Missing ids return **404** with `{"detail": "Deck {id} not found"}` (or Card).

### Seed data
| Deck id | Title | Cards |
|---------|-------|-------|
| `1` | Spanish basics | Hola, Gracias, Adiós |
| `2` | HTTP verbs | GET, POST |
"""

OPENAPI_TAGS = [
    {"name": "meta", "description": "Welcome pointer to the interactive docs."},
    {"name": "health", "description": "Liveness check for local runs and probes."},
    {
        "name": "decks",
        "description": "Deck CRUD, study sessions, and nested card list/create.",
    },
    {
        "name": "cards",
        "description": "Reveal, edit, or delete a single card by id.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.get("/", tags=["meta"], summary="Welcome")
    def root() -> dict[str, str]:
        return {"message": f"{settings.app_name} — see /docs for OpenAPI"}

    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
