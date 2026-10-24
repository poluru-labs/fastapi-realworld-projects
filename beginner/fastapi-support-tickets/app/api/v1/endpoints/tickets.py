from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_ticket_service
from app.schemas.ticket import (
    CommentCreate,
    CommentRead,
    TicketCreate,
    TicketDetail,
    TicketPriority,
    TicketRead,
    TicketStatus,
    TicketUpdate,
)
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get(
    "",
    response_model=list[TicketRead],
    summary="List support tickets",
    description=(
        "Sorted by most recently updated. Filter with `status`, `priority`, "
        "or search `q` in subject and description."
    ),
)
def list_tickets(
    service: Annotated[TicketService, Depends(get_ticket_service)],
    ticket_status: Annotated[
        TicketStatus | None,
        Query(alias="status", description="open, in_progress, resolved, or closed"),
    ] = None,
    priority: Annotated[TicketPriority | None, Query(description="low through urgent")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[TicketRead]:
    return service.list_tickets(status=ticket_status, priority=priority, q=q)


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket",
)
def create_ticket(
    payload: TicketCreate,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.create_ticket(payload)


@router.get(
    "/{ticket_id}",
    response_model=TicketDetail,
    summary="Ticket with comments",
)
def get_ticket(
    ticket_id: int,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketDetail:
    return service.get_ticket_detail(ticket_id)


@router.patch(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Update a ticket",
)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.update_ticket(ticket_id, payload)


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ticket",
    description="Removes the ticket and all of its comments.",
)
def delete_ticket(
    ticket_id: int,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> None:
    service.delete_ticket(ticket_id)


@router.get(
    "/{ticket_id}/comments",
    response_model=list[CommentRead],
    summary="List comments",
)
def list_comments(
    ticket_id: int,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> list[CommentRead]:
    return service.list_comments(ticket_id)


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
    responses={409: {"description": "Ticket is closed."}},
)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> CommentRead:
    return service.add_comment(ticket_id, payload)


@router.post(
    "/{ticket_id}/resolve",
    response_model=TicketRead,
    summary="Mark ticket resolved",
    responses={409: {"description": "Already resolved or closed."}},
)
def resolve_ticket(
    ticket_id: int,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.resolve_ticket(ticket_id)


@router.post(
    "/{ticket_id}/close",
    response_model=TicketRead,
    summary="Close a ticket",
    responses={409: {"description": "Already closed."}},
)
def close_ticket(
    ticket_id: int,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.close_ticket(ticket_id)


@router.post(
    "/{ticket_id}/reopen",
    response_model=TicketRead,
    summary="Reopen a resolved or closed ticket",
    responses={409: {"description": "Already open or in progress."}},
)
def reopen_ticket(
    ticket_id: int,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketRead:
    return service.reopen_ticket(ticket_id)
