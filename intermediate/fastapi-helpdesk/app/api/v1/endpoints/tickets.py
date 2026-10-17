from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_current_user, get_ticket_service
from app.schemas.ticket import (
    SLUG_PATTERN,
    TicketCreate,
    TicketPage,
    TicketPriority,
    TicketRead,
    TicketStatus,
    TicketUpdate,
)
from app.schemas.user import UserRead
from app.services.ticket_service import TicketService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        examples=["cannot-reset-password"],
    ),
]

_CREATE_EXAMPLES = {
    "account_issue": {
        "summary": "Save as draft before submit",
        "value": {
            "title": "Billing address will not save",
            "summary": "Checkout fails on step two.",
            "description": "The form clears when I click Continue.",
            "priority": "high",
            "tags": ["billing", "checkout"],
        },
    }
}


@router.get(
    "",
    response_model=TicketPage,
    summary="List support queue (admin)",
    description="Excludes drafts. Combine filters with AND.",
)
def list_queue(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
    ticket_status: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: Annotated[TicketPriority | None, Query()] = None,
    tag: Annotated[str | None, Query(max_length=32)] = None,
    assignee_id: Annotated[int | None, Query(ge=1)] = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketPage:
    return service.list_queue(
        actor,
        status=ticket_status,
        priority=priority,
        tag=tag,
        assignee_id=assignee_id,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.get("/mine", response_model=TicketPage, summary="List tickets you opened")
def list_my_tickets(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
    ticket_status: Annotated[TicketStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketPage:
    return service.list_mine(actor, status=ticket_status, limit=limit, offset=offset)


@router.get("/assigned", response_model=TicketPage, summary="List tickets assigned to you")
def list_assigned_tickets(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
    ticket_status: Annotated[TicketStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketPage:
    return service.list_assigned(actor, status=ticket_status, limit=limit, offset=offset)


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft ticket",
)
def create_ticket(
    payload: Annotated[TicketCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.create_ticket(actor, payload)


@router.get("/{slug}", response_model=TicketRead, summary="Get one ticket")
def get_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.get_ticket(actor, slug)


@router.patch("/{slug}", response_model=TicketRead, summary="Update ticket")
def update_ticket(
    slug: Slug,
    payload: TicketUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.update_ticket(actor, slug, payload)


@router.post("/{slug}/submit", response_model=TicketRead, summary="Submit draft to open queue")
def submit_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.submit(actor, slug)


@router.post("/{slug}/start", response_model=TicketRead, summary="Mark in progress")
def start_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.start(actor, slug)


@router.post("/{slug}/resolve", response_model=TicketRead, summary="Mark resolved")
def resolve_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.resolve(actor, slug)


@router.post("/{slug}/close", response_model=TicketRead, summary="Close ticket")
def close_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.close(actor, slug)


@router.post("/{slug}/reopen", response_model=TicketRead, summary="Reopen closed ticket")
def reopen_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.reopen(actor, slug)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete ticket")
def delete_ticket(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> None:
    service.delete_ticket(actor, slug)
