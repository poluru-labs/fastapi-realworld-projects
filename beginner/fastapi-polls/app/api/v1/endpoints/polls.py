from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_poll_service
from app.schemas.poll import PollCreate, PollDeleteResponse, PollRead, PollUpdate, VoteCreate
from app.services.poll_service import PollService

router = APIRouter()


@router.get(
    "",
    response_model=list[PollRead],
    summary="List polls",
    description="Return every poll with questions, options, and current vote totals.",
)
def list_polls(service: Annotated[PollService, Depends(get_poll_service)]) -> list[PollRead]:
    return service.list_polls()


@router.get(
    "/{poll_id}",
    response_model=PollRead,
    summary="Get poll by id",
    responses={404: {"description": "Poll not found"}},
)
def get_poll(
    poll_id: int,
    service: Annotated[PollService, Depends(get_poll_service)],
) -> PollRead:
    return service.get_poll(poll_id)


@router.post(
    "",
    response_model=PollRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create poll",
    description="Create a poll with a question and at least two unique answer options.",
)
def create_poll(
    payload: PollCreate,
    service: Annotated[PollService, Depends(get_poll_service)],
) -> PollRead:
    return service.create_poll(payload)


@router.put(
    "/{poll_id}",
    response_model=PollRead,
    summary="Replace poll",
    description="Replace the question and all options. Vote counts reset to zero.",
    responses={404: {"description": "Poll not found"}},
)
def replace_poll(
    poll_id: int,
    payload: PollCreate,
    service: Annotated[PollService, Depends(get_poll_service)],
) -> PollRead:
    return service.replace_poll(poll_id, payload)


@router.patch(
    "/{poll_id}",
    response_model=PollRead,
    summary="Update poll",
    description="Partially update the question and/or replace all options (resets votes).",
    responses={404: {"description": "Poll not found"}},
)
def update_poll(
    poll_id: int,
    payload: PollUpdate,
    service: Annotated[PollService, Depends(get_poll_service)],
) -> PollRead:
    return service.update_poll(poll_id, payload)


@router.post(
    "/{poll_id}/votes",
    response_model=PollRead,
    summary="Cast a vote",
    description="Increment the vote count for one option on the poll.",
    responses={
        404: {"description": "Poll or option not found"},
    },
)
def cast_vote(
    poll_id: int,
    payload: VoteCreate,
    service: Annotated[PollService, Depends(get_poll_service)],
) -> PollRead:
    return service.cast_vote(poll_id, payload)


@router.delete(
    "/{poll_id}",
    response_model=PollDeleteResponse,
    summary="Delete poll",
    responses={404: {"description": "Poll not found"}},
)
def delete_poll(
    poll_id: int,
    service: Annotated[PollService, Depends(get_poll_service)],
) -> PollDeleteResponse:
    removed = service.delete_poll(poll_id)
    return PollDeleteResponse(poll=removed)
