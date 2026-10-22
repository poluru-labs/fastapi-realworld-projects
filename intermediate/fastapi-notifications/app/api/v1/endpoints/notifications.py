from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_current_user, get_notification_service, require_roles
from app.schemas.notification import (
    NotificationDispatch,
    NotificationPage,
    NotificationPreferencesRead,
    NotificationPreferencesUpdate,
    NotificationRead,
    UnreadCount,
)
from app.schemas.user import UserRead, UserRole
from app.services.notification_service import NotificationService

router = APIRouter()

AdminUser = Annotated[UserRead, Depends(require_roles(UserRole.ADMIN))]


@router.get(
    "",
    response_model=NotificationPage,
    summary="List my notifications",
    description=(
        "Bearer required. Newest first. Set `unread_only=true` for a badge tray. "
        "`total` is the match count before `limit` and `offset`."
    ),
)
def list_notifications(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    unread_only: Annotated[bool, Query(description="When true, skip read items.")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationPage:
    return service.list_inbox(
        current_user,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCount,
    summary="Unread badge count",
)
def unread_count(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UnreadCount:
    return service.unread_count(current_user)


@router.post(
    "/read-all",
    response_model=UnreadCount,
    summary="Mark every notification read",
    description="Returns `{ \"unread\": 0 }` when finished.",
)
def mark_all_read(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> UnreadCount:
    return service.mark_all_read(current_user)


@router.get(
    "/preferences",
    response_model=NotificationPreferencesRead,
    summary="My delivery preferences",
    description="In-memory toggles for email and push channels (demo only).",
)
def get_preferences(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationPreferencesRead:
    return service.get_preferences(current_user)


@router.patch(
    "/preferences",
    response_model=NotificationPreferencesRead,
    summary="Update delivery preferences",
)
def update_preferences(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    payload: NotificationPreferencesUpdate,
) -> NotificationPreferencesRead:
    return service.update_preferences(current_user, payload)


@router.post(
    "/dispatch",
    response_model=NotificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Send a notification to a user",
    description="Platform admin only. Simulates a worker enqueueing an in-app message.",
)
def dispatch_notification(
    _: AdminUser,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    payload: NotificationDispatch,
) -> NotificationRead:
    return service.dispatch(payload)


@router.get(
    "/{notification_id}",
    response_model=NotificationRead,
    summary="Get one notification",
    description="Returns **404** when the id is missing or belongs to another user.",
)
def get_notification(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    notification_id: Annotated[int, Path(ge=1)],
) -> NotificationRead:
    return service.get_one(current_user, notification_id)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark one notification read",
    responses={409: {"description": "Already read."}},
)
def mark_notification_read(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    notification_id: int,
) -> NotificationRead:
    return service.mark_read(current_user, notification_id)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a notification",
)
def delete_notification(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    notification_id: int,
) -> None:
    service.delete(current_user, notification_id)
