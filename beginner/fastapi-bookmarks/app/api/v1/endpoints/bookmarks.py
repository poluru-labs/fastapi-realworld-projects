from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_bookmark_service
from app.schemas.bookmark import (
    BookmarkCreate,
    BookmarkDeleteResponse,
    BookmarkRead,
    BookmarkUpdate,
    TagListResponse,
)
from app.services.bookmark_service import BookmarkService

router = APIRouter()

_CREATE_EXAMPLES = {
    "docs": {
        "summary": "Save a documentation link",
        "value": {
            "title": "Pydantic docs",
            "url": "https://docs.pydantic.dev/latest/",
            "tags": ["python", "validation"],
            "note": "Models and settings.",
            "pinned": False,
        },
    }
}


@router.get(
    "/tags",
    response_model=TagListResponse,
    summary="List distinct tags",
    description="Returns all tags used by bookmarks, sorted alphabetically.",
)
def list_tags(
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> TagListResponse:
    return service.list_tags()


@router.get(
    "",
    response_model=list[BookmarkRead],
    summary="List bookmarks",
    description=(
        "Active bookmarks by default (`archived=false`). Pinned items appear first, "
        "then sorted by title. Use `search` to match title, URL, note, or tags."
    ),
)
def list_bookmarks(
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
    tag: Annotated[
        str | None,
        Query(description="Filter by tag (exact, case-insensitive)."),
    ] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
    pinned: Annotated[
        bool | None,
        Query(description="Filter pinned or unpinned."),
    ] = None,
    archived: Annotated[
        bool,
        Query(description="When true, list archived bookmarks only."),
    ] = False,
) -> list[BookmarkRead]:
    return service.list_bookmarks(tag=tag, search=search, pinned=pinned, archived=archived)


@router.get(
    "/{bookmark_id}",
    response_model=BookmarkRead,
    summary="Get bookmark",
)
def get_bookmark(
    bookmark_id: int,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkRead:
    return service.get_bookmark(bookmark_id)


@router.post(
    "",
    response_model=BookmarkRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create bookmark",
    description="URLs must be unique (trailing slashes and casing are normalized for comparison).",
)
def create_bookmark(
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
    payload: Annotated[BookmarkCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> BookmarkRead:
    return service.create_bookmark(payload)


@router.patch(
    "/{bookmark_id}",
    response_model=BookmarkRead,
    summary="Update bookmark",
)
def update_bookmark(
    bookmark_id: int,
    payload: BookmarkUpdate,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkRead:
    return service.update_bookmark(bookmark_id, payload)


@router.post(
    "/{bookmark_id}/pin",
    response_model=BookmarkRead,
    summary="Pin bookmark",
)
def pin_bookmark(
    bookmark_id: int,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkRead:
    return service.pin(bookmark_id)


@router.post(
    "/{bookmark_id}/unpin",
    response_model=BookmarkRead,
    summary="Unpin bookmark",
)
def unpin_bookmark(
    bookmark_id: int,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkRead:
    return service.unpin(bookmark_id)


@router.post(
    "/{bookmark_id}/archive",
    response_model=BookmarkRead,
    summary="Archive bookmark",
    description=(
        "Archived bookmarks are hidden from the default list "
        "until you query with `archived=true`."
    ),
)
def archive_bookmark(
    bookmark_id: int,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkRead:
    return service.archive(bookmark_id)


@router.post(
    "/{bookmark_id}/unarchive",
    response_model=BookmarkRead,
    summary="Restore archived bookmark",
)
def unarchive_bookmark(
    bookmark_id: int,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkRead:
    return service.unarchive(bookmark_id)


@router.delete(
    "/{bookmark_id}",
    response_model=BookmarkDeleteResponse,
    summary="Delete bookmark",
)
def delete_bookmark(
    bookmark_id: int,
    service: Annotated[BookmarkService, Depends(get_bookmark_service)],
) -> BookmarkDeleteResponse:
    return service.delete_bookmark(bookmark_id)
