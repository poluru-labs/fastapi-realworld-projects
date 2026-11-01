from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.policy import DocumentCreate, DocumentRead
from app.services.policy_service import PolicyService

router = APIRouter()


@router.get(
    "",
    response_model=list[DocumentRead],
    summary="List documents visible to caller",
    description="Each row is filtered through the same engine as `/policy/evaluate`.",
)
async def list_documents(
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> list[DocumentRead]:
    return await PolicyService(session, settings).list_documents(user.id)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document",
)
async def create_document(
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    payload: DocumentCreate,
) -> DocumentRead:
    return await PolicyService(session, settings).create_document(user.id, payload)


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Get one document",
)
async def get_document(
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    document_id: Annotated[int, Path(ge=1)],
) -> DocumentRead:
    return await PolicyService(session, settings).get_document(user.id, document_id)
