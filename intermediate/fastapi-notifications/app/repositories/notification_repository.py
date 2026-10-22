from dataclasses import dataclass
from datetime import datetime

from app.schemas.notification import NotificationType


@dataclass
class NotificationRecord:
    id: int
    user_id: int
    type: NotificationType
    title: str
    body: str
    data: dict
    read_at: datetime | None
    created_at: datetime


@dataclass
class PreferenceRecord:
    marketing_email: bool = True
    product_email: bool = True
    push_enabled: bool = True


def _seed_notifications() -> dict[int, NotificationRecord]:
    t0 = datetime.fromisoformat("2026-03-01T09:00:00+00:00")
    t1 = datetime.fromisoformat("2026-03-01T10:00:00+00:00")
    t2 = datetime.fromisoformat("2026-03-01T11:00:00+00:00")
    t3 = datetime.fromisoformat("2026-03-02T08:00:00+00:00")
    return {
        1: NotificationRecord(
            id=1,
            user_id=1,
            type=NotificationType.SYSTEM,
            title="Welcome to Notifications API",
            body="Seed inbox for the platform admin. Try mark-read and filters in /docs.",
            data={"doc_path": "/docs"},
            read_at=None,
            created_at=t0,
        ),
        2: NotificationRecord(
            id=2,
            user_id=1,
            type=NotificationType.REMINDER,
            title="Review unread count",
            body="GET /api/v1/notifications/unread-count returns a badge-friendly number.",
            data={},
            read_at=None,
            created_at=t1,
        ),
        3: NotificationRecord(
            id=3,
            user_id=1,
            type=NotificationType.MENTION,
            title="You were mentioned in #general",
            body="Demo user pinged you while testing mention notifications.",
            data={"channel": "general", "actor": "demo@example.com"},
            read_at=t2,
            created_at=t1,
        ),
        4: NotificationRecord(
            id=4,
            user_id=2,
            type=NotificationType.SYSTEM,
            title="Your account is ready",
            body="Sign in and open your inbox. Preferences live under /notifications/preferences.",
            data={},
            read_at=None,
            created_at=t3,
        ),
    }


class NotificationRepository:
    """In-memory notifications per user. Restart restores seed rows only."""

    def __init__(self) -> None:
        self._by_id = dict(_seed_notifications())
        self._next_id = max(self._by_id.keys(), default=0) + 1
        self._preferences: dict[int, PreferenceRecord] = {
            1: PreferenceRecord(),
            2: PreferenceRecord(marketing_email=False),
        }

    def list_for_user(self, user_id: int) -> list[NotificationRecord]:
        return [row for row in self._by_id.values() if row.user_id == user_id]

    def get(self, notification_id: int) -> NotificationRecord | None:
        return self._by_id.get(notification_id)

    def add(self, record: NotificationRecord) -> NotificationRecord:
        self._by_id[record.id] = record
        return record

    def allocate_id(self) -> int:
        notification_id = self._next_id
        self._next_id += 1
        return notification_id

    def delete(self, notification_id: int) -> None:
        self._by_id.pop(notification_id, None)

    def get_preferences(self, user_id: int) -> PreferenceRecord:
        prefs = self._preferences.get(user_id)
        if prefs is None:
            prefs = PreferenceRecord()
            self._preferences[user_id] = prefs
        return prefs

    def save_preferences(self, user_id: int, prefs: PreferenceRecord) -> PreferenceRecord:
        self._preferences[user_id] = prefs
        return prefs
