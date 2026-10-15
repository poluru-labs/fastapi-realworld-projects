from typing import Annotated

from fastapi import APIRouter, Body, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.webhook import (
    WebhookEndpointCreate,
    WebhookEndpointCreated,
    WebhookEndpointRead,
    WebhookEndpointUpdate,
)
from app.services.endpoint_service import EndpointService

router = APIRouter(prefix="/webhook-endpoints", tags=["webhook-endpoints"])

_CREATE_EXAMPLES = {
    "capture": {
        "summary": "Deliver to the built-in capture sink",
        "value": {
            "url": "http://testserver/api/v1/dev/capture",
            "description": "Local demo receiver",
            "event_types": ["*"],
        },
    }
}


@router.get("", response_model=list[WebhookEndpointRead], summary="List your webhook endpoints")
async def list_endpoints(user: CurrentUser, session: DbSession) -> list[WebhookEndpointRead]:
    return await EndpointService(session).list_endpoints(user)


@router.get(
    "/{endpoint_id}",
    response_model=WebhookEndpointRead,
    summary="Get one webhook endpoint",
    description="Another user's endpoint id returns **404**, not **403**.",
)
async def get_endpoint(
    endpoint_id: int,
    user: CurrentUser,
    session: DbSession,
) -> WebhookEndpointRead:
    return await EndpointService(session).get_endpoint(user, endpoint_id)


@router.post(
    "",
    response_model=WebhookEndpointCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Register a webhook endpoint",
    description="The `signing_secret` is returned once. Store it on your subscriber.",
)
async def create_endpoint(
    user: CurrentUser,
    session: DbSession,
    payload: Annotated[WebhookEndpointCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> WebhookEndpointCreated:
    return await EndpointService(session).create_endpoint(user, payload)


@router.patch("/{endpoint_id}", response_model=WebhookEndpointRead, summary="Update endpoint")
async def update_endpoint(
    endpoint_id: int,
    payload: WebhookEndpointUpdate,
    user: CurrentUser,
    session: DbSession,
) -> WebhookEndpointRead:
    return await EndpointService(session).update_endpoint(user, endpoint_id, payload)
