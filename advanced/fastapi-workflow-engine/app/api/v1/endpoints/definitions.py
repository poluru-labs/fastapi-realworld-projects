from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from app.api.deps import AdminUser, DbSession, OptionalUser
from app.schemas.workflow import (
    DefinitionStatus,
    WorkflowDefinitionCreate,
    WorkflowDefinitionRead,
    WorkflowDefinitionUpdate,
)
from app.services.definition_service import DefinitionService

router = APIRouter(prefix="/workflow-definitions", tags=["workflow-definitions"])

_CREATE_EXAMPLES = {
    "approval": {
        "summary": "Two-step approval graph",
        "value": {
            "slug": "document-approval",
            "name": "Document approval",
            "description": "Submit then approve.",
            "initial_state": "submitted",
            "states": ["submitted", "approved"],
            "transitions": [
                {"action": "approve", "from": "submitted", "to": "approved", "roles": ["admin"]}
            ],
            "terminal_states": ["approved"],
        },
    }
}


@router.get(
    "",
    response_model=list[WorkflowDefinitionRead],
    summary="List workflow definitions",
    description=(
        "Anonymous callers see **published** definitions only. "
        "Admins may filter drafts or archived rows with `status`."
    ),
)
async def list_definitions(
    session: DbSession,
    actor: OptionalUser,
    definition_status: Annotated[
        DefinitionStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[WorkflowDefinitionRead]:
    return await DefinitionService(session).list_definitions(actor, status=definition_status)


@router.get(
    "/{slug}",
    response_model=WorkflowDefinitionRead,
    summary="Get one workflow definition",
    description="Draft and archived definitions return **404** to non-admins.",
)
async def get_definition(
    slug: str,
    session: DbSession,
    actor: OptionalUser,
) -> WorkflowDefinitionRead:
    return await DefinitionService(session).get_definition(actor, slug)


@router.post(
    "",
    response_model=WorkflowDefinitionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft definition (admin)",
)
async def create_definition(
    admin: AdminUser,
    session: DbSession,
    payload: Annotated[WorkflowDefinitionCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> WorkflowDefinitionRead:
    return await DefinitionService(session).create_definition(admin, payload)


@router.patch(
    "/{slug}",
    response_model=WorkflowDefinitionRead,
    summary="Update a draft definition (admin)",
)
async def update_definition(
    slug: str,
    payload: WorkflowDefinitionUpdate,
    admin: AdminUser,
    session: DbSession,
) -> WorkflowDefinitionRead:
    return await DefinitionService(session).update_definition(admin, slug, payload)


@router.post(
    "/{slug}/publish",
    response_model=WorkflowDefinitionRead,
    summary="Publish definition (admin)",
)
async def publish_definition(
    slug: str,
    admin: AdminUser,
    session: DbSession,
) -> WorkflowDefinitionRead:
    return await DefinitionService(session).publish(admin, slug)


@router.post(
    "/{slug}/archive",
    response_model=WorkflowDefinitionRead,
    summary="Archive definition (admin)",
)
async def archive_definition(
    slug: str,
    admin: AdminUser,
    session: DbSession,
) -> WorkflowDefinitionRead:
    return await DefinitionService(session).archive(admin, slug)


@router.post(
    "/{slug}/restore",
    response_model=WorkflowDefinitionRead,
    summary="Restore archived definition to draft (admin)",
)
async def restore_definition(
    slug: str,
    admin: AdminUser,
    session: DbSession,
) -> WorkflowDefinitionRead:
    return await DefinitionService(session).restore_draft(admin, slug)
