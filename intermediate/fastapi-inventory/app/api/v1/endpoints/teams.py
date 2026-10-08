from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.api.deps import get_current_user, get_team_service
from app.schemas.team import MemberAdd, MemberRead, TeamCreate, TeamRead, TeamUpdate
from app.schemas.user import UserRead
from app.services.team_service import TeamService

router = APIRouter()

_CREATE_EXAMPLES = {
    "design": {
        "summary": "New team",
        "description": "The caller becomes the owner and the only member.",
        "value": {"name": "Design", "description": "Interface work for the board"},
    }
}


@router.get(
    "",
    response_model=list[TeamRead],
    summary="List teams you can see",
    description=(
        "Members see teams they have joined. A platform admin sees every team, "
        "including ones they have not joined (`team_role` is then null)."
    ),
)
def list_teams(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> list[TeamRead]:
    return service.list_teams(actor)


@router.post(
    "",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a team",
    description="Any signed-in user can create a team. The name must be unique, ignoring case.",
    responses={409: {"description": "Another team already uses this name."}},
)
def create_team(
    payload: Annotated[TeamCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamRead:
    return service.create_team(actor, payload)


@router.get(
    "/{team_id}",
    response_model=TeamRead,
    summary="Get one team",
    description="Caller must be a member, or a platform admin.",
    responses={
        403: {"description": "Signed in, but not a member of this team."},
        404: {"description": "No team with this id."},
    },
)
def get_team(
    team_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamRead:
    return service.get_team(actor, team_id)


@router.patch(
    "/{team_id}",
    response_model=TeamRead,
    summary="Update team name or description",
    description="Team owner or platform admin. Omitted fields stay as they are.",
    responses={403: {"description": "Caller is a member but not the owner."}},
)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamRead:
    return service.update_team(actor, team_id, payload)


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a team and its tasks",
    description="Team owner or platform admin. Tasks on the team are deleted with it.",
)
def delete_team(
    team_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    service.delete_team(actor, team_id)


@router.get(
    "/{team_id}/members",
    response_model=list[MemberRead],
    summary="List team members",
    description="Includes the owner. Caller must be a member or a platform admin.",
)
def list_members(
    team_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> list[MemberRead]:
    return service.list_members(actor, team_id)


@router.post(
    "/{team_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member by email",
    description=(
        "Owner or platform admin. The email must belong to an existing active user. "
        "New members join as `member`, never as a second owner."
    ),
    responses={
        404: {"description": "No active user with that email."},
        409: {"description": "That user is already on the team."},
    },
)
def add_member(
    team_id: int,
    payload: MemberAdd,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> MemberRead:
    return service.add_member(actor, team_id, payload)


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member",
    description=(
        "Owner or platform admin. The owner cannot be removed. "
        "Tasks assigned to the removed user become unassigned."
    ),
    responses={409: {"description": "Refusing to remove the owner."}},
)
def remove_member(
    team_id: int,
    user_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    service.remove_member(actor, team_id, user_id)
