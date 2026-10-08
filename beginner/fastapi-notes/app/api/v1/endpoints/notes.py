from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_note_service
from app.schemas.note import NoteCreate, NoteDeleteResponse, NoteRead, NoteUpdate
from app.services.note_service import NoteService

router = APIRouter()

_CREATE_EXAMPLES = {
    "plain": {
        "summary": "A new note",
        "description": "Title is required. Body and pinned have defaults.",
        "value": {
            "title": "Ideas for the walkthrough",
            "body": "Show search, then pin.",
        },
    },
    "pinned_note": {
        "summary": "A note that starts pinned",
        "description": "Set pinned to true when the note should appear at the top.",
        "value": {
            "title": "Remember the port",
            "body": "uvicorn defaults to port 8000.",
            "pinned": True,
        },
    },
}

_UPDATE_EXAMPLES = {
    "rewrite_body": {
        "summary": "Change the body only",
        "description": "Omitted fields stay as they are.",
        "value": {"body": "Show search, pin, and delete."},
    },
    "rename": {
        "summary": "Rename the note",
        "value": {"title": "Walkthrough checklist"},
    },
}


@router.get(
    "",
    response_model=list[NoteRead],
    summary="List notes",
    description=(
        "Pinned notes come first. Within each group, smaller ids come first. "
        "Pass pinned to keep only pinned or unpinned notes. "
        "Pass search to match title or body, ignoring case. Both can be used together. "
        "A blank search is ignored."
    ),
)
def list_notes(
    service: Annotated[NoteService, Depends(get_note_service)],
    pinned: Annotated[
        bool | None,
        Query(description="true for pinned notes, false for the rest."),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=80,
            description="Case-insensitive text matched against title and body.",
        ),
    ] = None,
) -> list[NoteRead]:
    return service.list_notes(pinned=pinned, search=search)


@router.get(
    "/{note_id}",
    response_model=NoteRead,
    summary="Get a note",
    responses={404: {"description": "No note has that id."}},
)
def get_note(
    note_id: int,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteRead:
    return service.get_note(note_id)


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
    description=(
        "Title is required, 1–120 characters after leading and trailing spaces are removed. "
        "Body may be blank and is at most 2000 characters. "
        "Pinned defaults to false."
    ),
    responses={422: {"description": "The body failed validation."}},
)
def create_note(
    payload: Annotated[NoteCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteRead:
    return service.create_note(payload)


@router.patch(
    "/{note_id}",
    response_model=NoteRead,
    summary="Update a note",
    description=(
        "Send only the fields you want to change. "
        "An empty body returns the note unchanged. "
        "Setting pinned here is the same as pin or unpin."
    ),
    responses={
        404: {"description": "No note has that id."},
        422: {"description": "A sent field failed validation."},
    },
)
def update_note(
    note_id: int,
    payload: Annotated[NoteUpdate, Body(openapi_examples=_UPDATE_EXAMPLES)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteRead:
    return service.update_note(note_id, payload)


@router.post(
    "/{note_id}/pin",
    response_model=NoteRead,
    summary="Pin a note",
    description="Sets pinned to true. Calling it again on a pinned note leaves the note as it is.",
    responses={404: {"description": "No note has that id."}},
)
def pin_note(
    note_id: int,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteRead:
    return service.pin_note(note_id)


@router.post(
    "/{note_id}/unpin",
    response_model=NoteRead,
    summary="Unpin a note",
    description=(
        "Sets pinned to false. Calling it again on an unpinned note leaves the note as it is."
    ),
    responses={404: {"description": "No note has that id."}},
)
def unpin_note(
    note_id: int,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteRead:
    return service.unpin_note(note_id)


@router.delete(
    "/{note_id}",
    response_model=NoteDeleteResponse,
    summary="Delete a note",
    description="Removes the note and returns a snapshot of what was deleted.",
    responses={404: {"description": "No note has that id."}},
)
def delete_note(
    note_id: int,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteDeleteResponse:
    removed = service.delete_note(note_id)
    return NoteDeleteResponse(note=removed)
