from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_current_user, get_document_service, get_optional_user
from app.schemas.document import (
    DocumentCreate,
    DocumentPage,
    DocumentRead,
    DocumentStatus,
    DocumentUpdate,
    RevisionRead,
)
from app.schemas.folder import SLUG_PATTERN as FOLDER_SLUG_PATTERN
from app.schemas.user import UserRead
from app.services.document_service import DocumentService

router = APIRouter()

FolderSlug = Annotated[
    str,
    Path(pattern=FOLDER_SLUG_PATTERN.pattern, min_length=1, max_length=80),
]
DocSlug = Annotated[
    str,
    Path(pattern=FOLDER_SLUG_PATTERN.pattern, min_length=1, max_length=80),
]

_OPTIONAL_BEARER = {"security": [{}, {"OAuth2PasswordBearer": []}]}


@router.get(
    "",
    response_model=DocumentPage,
    summary="List documents in a folder",
    description=(
        "Published documents are visible to anonymous callers. Drafts and archived "
        "documents require the author token or an admin."
    ),
    openapi_extra=_OPTIONAL_BEARER,
)
def list_documents(
    folder_slug: FolderSlug,
    service: Annotated[DocumentService, Depends(get_document_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)] = None,
    status_filter: Annotated[
        DocumentStatus | None,
        Query(alias="status", description="Filter by workflow status."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentPage:
    return service.list_in_folder(
        actor,
        folder_slug,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft document",
)
def create_document(
    folder_slug: FolderSlug,
    payload: DocumentCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return service.create_document(current_user, folder_slug, payload)


@router.get(
    "/{doc_slug}",
    response_model=DocumentRead,
    summary="Read a document",
    openapi_extra=_OPTIONAL_BEARER,
)
def get_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    service: Annotated[DocumentService, Depends(get_document_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)] = None,
) -> DocumentRead:
    return service.get_document(actor, folder_slug, doc_slug)


@router.patch(
    "/{doc_slug}",
    response_model=DocumentRead,
    summary="Update document content",
)
def update_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    payload: DocumentUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return service.update_document(current_user, folder_slug, doc_slug, payload)


@router.post(
    "/{doc_slug}/publish",
    response_model=DocumentRead,
    summary="Publish a draft",
    description="Increments `version` and stores an immutable revision snapshot.",
)
def publish_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return service.publish(current_user, folder_slug, doc_slug)


@router.post(
    "/{doc_slug}/unpublish",
    response_model=DocumentRead,
    summary="Move a published document back to draft",
)
def unpublish_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return service.unpublish(current_user, folder_slug, doc_slug)


@router.post(
    "/{doc_slug}/archive",
    response_model=DocumentRead,
    summary="Archive a published document",
)
def archive_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return service.archive(current_user, folder_slug, doc_slug)


@router.post(
    "/{doc_slug}/restore",
    response_model=DocumentRead,
    summary="Restore an archived document to draft",
)
def restore_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return service.restore(current_user, folder_slug, doc_slug)


@router.get(
    "/{doc_slug}/revisions",
    response_model=list[RevisionRead],
    summary="List publish revisions",
    description="Author-only history of published snapshots.",
)
def list_revisions(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[RevisionRead]:
    return service.list_revisions(current_user, folder_slug, doc_slug)


@router.delete(
    "/{doc_slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
def delete_document(
    folder_slug: FolderSlug,
    doc_slug: DocSlug,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    service.delete_document(current_user, folder_slug, doc_slug)
