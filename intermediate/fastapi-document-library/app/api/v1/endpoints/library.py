from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_document_service
from app.schemas.document import DocumentPage, TagCount
from app.services.document_service import DocumentService

router = APIRouter()


@router.get(
    "/documents",
    response_model=DocumentPage,
    summary="Search published documents",
    description=(
        "Public index across all folders. Drafts and archived documents never appear. "
        "Filters combine with AND. Newest `published_at` first."
    ),
)
def search_documents(
    service: Annotated[DocumentService, Depends(get_document_service)],
    tag: Annotated[str | None, Query(max_length=32)] = None,
    folder_slug: Annotated[str | None, Query(max_length=80)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentPage:
    return service.list_published_library(
        tag=tag,
        folder_slug=folder_slug,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tags",
    response_model=list[TagCount],
    summary="Tags on published documents",
)
def list_tags(
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[TagCount]:
    return service.list_tags()
