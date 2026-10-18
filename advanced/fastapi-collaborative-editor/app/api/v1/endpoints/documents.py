from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from app.api.deps import CurrentUser, DocumentServiceDep
from app.schemas.editor import (
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
    MembershipRead,
    SeenRevisionUpdate,
)

router = APIRouter(prefix="/documents", tags=["documents"])

_CREATE_EXAMPLES = {
    "playbook": {
        "summary": "Shared team doc",
        "value": {
            "slug": "team-playbook",
            "title": "Team playbook",
            "body": "Welcome collaborators.",
            "visibility": "public",
        },
    }
}


@router.get("", response_model=list[DocumentRead], summary="List public active documents")
async def list_public_documents(
    service: DocumentServiceDep,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DocumentRead]:
    _ = user
    return await service.list_public(limit=limit, offset=offset)


@router.get("/mine", response_model=list[DocumentRead], summary="Documents you belong to")
async def list_my_documents(
    service: DocumentServiceDep,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DocumentRead]:
    return await service.list_mine(user, limit=limit, offset=offset)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document",
)
async def create_document(
    service: DocumentServiceDep,
    user: CurrentUser,
    payload: Annotated[DocumentCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> DocumentRead:
    return await service.create(user, payload)


@router.get("/{slug}", response_model=DocumentRead, summary="Get document snapshot")
async def get_document(
    slug: str,
    service: DocumentServiceDep,
    user: CurrentUser,
) -> DocumentRead:
    return await service.get_document(user, slug)


@router.patch("/{slug}", response_model=DocumentRead, summary="Update document title")
async def update_document(
    slug: str,
    payload: DocumentUpdate,
    service: DocumentServiceDep,
    user: CurrentUser,
) -> DocumentRead:
    return await service.update_document(user, slug, payload)


@router.post("/{slug}/join", response_model=MembershipRead, summary="Join a public document")
async def join_document(
    slug: str,
    service: DocumentServiceDep,
    user: CurrentUser,
) -> MembershipRead:
    return await service.join(user, slug)


@router.post("/{slug}/archive", response_model=DocumentRead, summary="Archive document")
async def archive_document(
    slug: str,
    service: DocumentServiceDep,
    user: CurrentUser,
) -> DocumentRead:
    return await service.archive(user, slug)


@router.patch(
    "/{slug}/members/me/seen",
    response_model=MembershipRead,
    summary="Update last seen revision",
)
async def update_seen_revision(
    slug: str,
    payload: SeenRevisionUpdate,
    service: DocumentServiceDep,
    user: CurrentUser,
) -> MembershipRead:
    return await service.update_seen_revision(user, slug, payload)
