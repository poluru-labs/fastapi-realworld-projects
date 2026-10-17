from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_entry_service
from app.schemas.entry import (
    EntryCreate,
    EntryDeleteResponse,
    EntryRead,
    EntryUpdate,
    Mood,
    TagListResponse,
)
from app.services.entry_service import EntryService

router = APIRouter()

_CREATE_EXAMPLES = {
    "daily": {
        "summary": "Log today",
        "value": {
            "entry_date": "2026-10-16",
            "title": "Morning reflection",
            "body": "Started the day with a short walk and planning.",
            "mood": "good",
            "tags": ["health", "planning"],
        },
    }
}


@router.get(
    "/tags",
    response_model=TagListResponse,
    summary="List distinct tags",
)
def list_tags(
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> TagListResponse:
    return service.list_tags()


@router.get(
    "",
    response_model=list[EntryRead],
    summary="List journal entries",
    description="Starred entries first, then newest `entry_date`. Filters combine with AND.",
)
def list_entries(
    service: Annotated[EntryService, Depends(get_entry_service)],
    tag: Annotated[str | None, Query(max_length=32)] = None,
    mood: Annotated[Mood | None, Query(description="Filter by mood.")] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
    starred: Annotated[bool | None, Query()] = None,
    date_from: Annotated[date | None, Query(description="Inclusive start date.")] = None,
    date_to: Annotated[date | None, Query(description="Inclusive end date.")] = None,
) -> list[EntryRead]:
    return service.list_entries(
        tag=tag,
        mood=mood.value if mood else None,
        search=search,
        starred=starred,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/by-date/{entry_date}",
    response_model=EntryRead,
    summary="Get entry for a calendar day",
)
def get_entry_by_date(
    entry_date: date,
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> EntryRead:
    return service.get_by_date(entry_date)


@router.get(
    "/{entry_id}",
    response_model=EntryRead,
    summary="Get entry by id",
)
def get_entry(
    entry_id: int,
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> EntryRead:
    return service.get_entry(entry_id)


@router.post(
    "",
    response_model=EntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create entry",
    description="One entry per `entry_date`. Duplicates return **409**.",
)
def create_entry(
    service: Annotated[EntryService, Depends(get_entry_service)],
    payload: Annotated[EntryCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> EntryRead:
    return service.create_entry(payload)


@router.patch(
    "/{entry_id}",
    response_model=EntryRead,
    summary="Update entry",
    description="`entry_date` cannot change; delete and recreate for a different day.",
)
def update_entry(
    entry_id: int,
    payload: EntryUpdate,
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> EntryRead:
    return service.update_entry(entry_id, payload)


@router.post("/{entry_id}/star", response_model=EntryRead, summary="Star entry")
def star_entry(
    entry_id: int,
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> EntryRead:
    return service.star(entry_id)


@router.post("/{entry_id}/unstar", response_model=EntryRead, summary="Remove star")
def unstar_entry(
    entry_id: int,
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> EntryRead:
    return service.unstar(entry_id)


@router.delete(
    "/{entry_id}",
    response_model=EntryDeleteResponse,
    summary="Delete entry",
)
def delete_entry(
    entry_id: int,
    service: Annotated[EntryService, Depends(get_entry_service)],
) -> EntryDeleteResponse:
    return service.delete_entry(entry_id)
