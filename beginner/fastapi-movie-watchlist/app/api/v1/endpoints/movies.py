from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_movie_service
from app.schemas.movie import (
    MovieCreate,
    MovieDeleteResponse,
    MovieRead,
    MovieUpdate,
    WatchStatus,
)
from app.services.movie_service import MovieService

router = APIRouter()

_CREATE_EXAMPLES = {
    "full": {
        "summary": "Movie with IMDb id",
        "description": "IMDb id must be unique when provided.",
        "value": {
            "title": "The Matrix",
            "director": "Lana Wachowski, Lilly Wachowski",
            "imdb_id": "tt0133093",
            "genre": "Science Fiction",
            "release_year": 1999,
            "runtime_minutes": 136,
            "status": "want_to_watch",
            "pinned": False,
        },
    },
    "minimal": {
        "summary": "Title and director only",
        "value": {
            "title": "Local film festival pick",
            "director": "Various",
            "genre": "Documentary",
        },
    },
}

_UPDATE_EXAMPLES = {
    "watching": {
        "summary": "Start watching",
        "value": {"status": "watching"},
    },
    "clear_imdb": {
        "summary": "Remove IMDb id from record",
        "value": {"imdb_id": ""},
    },
}


@router.get(
    "/genres",
    response_model=list[str],
    summary="List distinct genres",
    description="Sorted alphabetically from movies currently on the watchlist.",
)
def list_genres(service: Annotated[MovieService, Depends(get_movie_service)]) -> list[str]:
    return service.list_genres()


@router.get(
    "",
    response_model=list[MovieRead],
    summary="List movies",
    description=(
        "Pinned titles appear first, then smaller ids. "
        "Filter with `genre`, `status`, `pinned`, and `search`. "
        "`search` matches title, director, or IMDb id (case insensitive)."
    ),
)
def list_movies(
    service: Annotated[MovieService, Depends(get_movie_service)],
    genre: Annotated[str | None, Query(description="Exact genre match (case insensitive).")] = None,
    search: Annotated[str | None, Query(description="Substring search.")] = None,
    watch_status: Annotated[
        WatchStatus | None,
        Query(alias="status", description="want_to_watch, watching, or watched."),
    ] = None,
    pinned: Annotated[bool | None, Query(description="Filter pinned (watch next) titles.")] = None,
) -> list[MovieRead]:
    return service.list_movies(
        genre=genre,
        search=search,
        status=watch_status,
        pinned=pinned,
    )


@router.get("/{movie_id}", response_model=MovieRead, summary="Get one movie")
def get_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieRead:
    return service.get_movie(movie_id)


@router.post(
    "",
    response_model=MovieRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie",
)
def create_movie(
    service: Annotated[MovieService, Depends(get_movie_service)],
    payload: Annotated[MovieCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> MovieRead:
    return service.create_movie(payload)


@router.put("/{movie_id}", response_model=MovieRead, summary="Replace a movie")
def replace_movie(
    movie_id: int,
    payload: MovieCreate,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieRead:
    return service.replace_movie(movie_id, payload)


@router.patch(
    "/{movie_id}",
    response_model=MovieRead,
    summary="Partial update",
)
def update_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    payload: Annotated[MovieUpdate, Body(openapi_examples=_UPDATE_EXAMPLES)],
) -> MovieRead:
    return service.update_movie(movie_id, payload)


@router.post("/{movie_id}/pin", response_model=MovieRead, summary="Pin (watch next)")
def pin_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieRead:
    return service.pin_movie(movie_id)


@router.post("/{movie_id}/unpin", response_model=MovieRead, summary="Remove pin")
def unpin_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieRead:
    return service.unpin_movie(movie_id)


@router.post(
    "/{movie_id}/mark-watched",
    response_model=MovieRead,
    summary="Mark as watched",
    description="Sets `status` to **watched** without sending a PATCH body.",
)
def mark_watched(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieRead:
    return service.mark_watched(movie_id)


@router.delete("/{movie_id}", response_model=MovieDeleteResponse, summary="Remove from watchlist")
def delete_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieDeleteResponse:
    removed = service.delete_movie(movie_id)
    return MovieDeleteResponse(movie=removed)
