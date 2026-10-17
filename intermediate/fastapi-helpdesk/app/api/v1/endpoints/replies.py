from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_current_user, get_reply_service
from app.schemas.reply import ReplyCreate, ReplyPage, ReplyRead
from app.schemas.ticket import SLUG_PATTERN
from app.schemas.user import UserRead
from app.services.reply_service import ReplyService

router = APIRouter()

Slug = Annotated[str, Path(pattern=SLUG_PATTERN.pattern, min_length=1, max_length=80)]

_CREATE_EXAMPLES = {
    "customer_update": {
        "value": {"message": "I still cannot log in after clearing cookies."},
    }
}


@router.get("", response_model=ReplyPage, summary="List replies on a ticket")
def list_replies(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReplyService, Depends(get_reply_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReplyPage:
    return service.list_replies(actor, slug, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ReplyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a reply",
    description="Allowed while the ticket is open, in progress, or resolved.",
)
def create_reply(
    slug: Slug,
    payload: Annotated[ReplyCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReplyService, Depends(get_reply_service)],
) -> ReplyRead:
    return service.create_reply(actor, slug, payload)


@router.delete("/{reply_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a reply")
def delete_reply(
    slug: Slug,
    reply_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ReplyService, Depends(get_reply_service)],
) -> None:
    service.delete_reply(actor, slug, reply_id)
