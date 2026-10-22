from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.notification_repository import NotificationRecord, NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.notification import (
    NotificationDispatch,
    NotificationPage,
    NotificationPreferencesRead,
    NotificationPreferencesUpdate,
    NotificationRead,
    UnreadCount,
)
from app.schemas.user import UserRead


class NotificationService:
    def __init__(
        self,
        notifications: NotificationRepository,
        users: UserRepository,
    ) -> None:
        self._notifications = notifications
        self._users = users

    def list_inbox(
        self,
        current_user: UserRead,
        *,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> NotificationPage:
        rows = self._notifications.list_for_user(current_user.id)
        rows.sort(key=lambda row: row.created_at, reverse=True)
        if unread_only:
            rows = [row for row in rows if row.read_at is None]
        total = len(rows)
        page = rows[offset : offset + limit]
        return NotificationPage(
            items=[self._to_read(row) for row in page],
            total=total,
            limit=limit,
            offset=offset,
        )

    def unread_count(self, current_user: UserRead) -> UnreadCount:
        rows = self._notifications.list_for_user(current_user.id)
        unread = sum(1 for row in rows if row.read_at is None)
        return UnreadCount(unread=unread)

    def get_one(self, current_user: UserRead, notification_id: int) -> NotificationRead:
        return self._to_read(self._require_owned(current_user, notification_id))

    def mark_read(self, current_user: UserRead, notification_id: int) -> NotificationRead:
        record = self._require_owned(current_user, notification_id)
        if record.read_at is not None:
            raise ConflictError("Notification is already read")
        record.read_at = datetime.now(UTC)
        return self._to_read(record)

    def mark_all_read(self, current_user: UserRead) -> UnreadCount:
        now = datetime.now(UTC)
        for row in self._notifications.list_for_user(current_user.id):
            if row.read_at is None:
                row.read_at = now
        return self.unread_count(current_user)

    def delete(self, current_user: UserRead, notification_id: int) -> None:
        self._require_owned(current_user, notification_id)
        self._notifications.delete(notification_id)

    def dispatch(self, payload: NotificationDispatch) -> NotificationRead:
        if self._users.get_by_id(payload.user_id) is None:
            raise NotFoundError("User", str(payload.user_id))
        now = datetime.now(UTC)
        record = NotificationRecord(
            id=self._notifications.allocate_id(),
            user_id=payload.user_id,
            type=payload.type,
            title=payload.title,
            body=payload.body,
            data=dict(payload.data),
            read_at=None,
            created_at=now,
        )
        self._notifications.add(record)
        return self._to_read(record)

    def get_preferences(self, current_user: UserRead) -> NotificationPreferencesRead:
        prefs = self._notifications.get_preferences(current_user.id)
        return NotificationPreferencesRead(
            marketing_email=prefs.marketing_email,
            product_email=prefs.product_email,
            push_enabled=prefs.push_enabled,
        )

    def update_preferences(
        self,
        current_user: UserRead,
        payload: NotificationPreferencesUpdate,
    ) -> NotificationPreferencesRead:
        prefs = self._notifications.get_preferences(current_user.id)
        if payload.marketing_email is not None:
            prefs.marketing_email = payload.marketing_email
        if payload.product_email is not None:
            prefs.product_email = payload.product_email
        if payload.push_enabled is not None:
            prefs.push_enabled = payload.push_enabled
        self._notifications.save_preferences(current_user.id, prefs)
        return self.get_preferences(current_user)

    def _require_owned(self, current_user: UserRead, notification_id: int) -> NotificationRecord:
        record = self._notifications.get(notification_id)
        if record is None or record.user_id != current_user.id:
            raise NotFoundError("Notification", str(notification_id))
        return record

    @staticmethod
    def _to_read(record: NotificationRecord) -> NotificationRead:
        return NotificationRead(
            id=record.id,
            user_id=record.user_id,
            type=record.type,
            title=record.title,
            body=record.body,
            data=dict(record.data),
            read_at=record.read_at,
            created_at=record.created_at,
        )
