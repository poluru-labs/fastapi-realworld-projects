from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.course import EnrollmentStatus


@dataclass
class EnrollmentRecord:
    id: int
    user_id: int
    course_id: int
    status: EnrollmentStatus
    enrolled_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


@dataclass
class LessonProgressRecord:
    enrollment_id: int
    lesson_id: int
    completed_at: datetime = field(default_factory=datetime.now)


class EnrollmentRepository:
    def __init__(self) -> None:
        self._enrollments: dict[int, EnrollmentRecord] = {}
        self._progress: dict[tuple[int, int], LessonProgressRecord] = {}
        self._next_id = 1

    def get(self, enrollment_id: int) -> EnrollmentRecord | None:
        return self._enrollments.get(enrollment_id)

    def list_for_user(self, user_id: int) -> list[EnrollmentRecord]:
        return [row for row in self._enrollments.values() if row.user_id == user_id]

    def list_all(self) -> list[EnrollmentRecord]:
        return list(self._enrollments.values())

    def active_for_user_course(self, user_id: int, course_id: int) -> EnrollmentRecord | None:
        for row in self._enrollments.values():
            if (
                row.user_id == user_id
                and row.course_id == course_id
                and row.status is EnrollmentStatus.ACTIVE
            ):
                return row
        return None

    def allocate_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def add(self, record: EnrollmentRecord) -> None:
        self._enrollments[record.id] = record

    def save(self, record: EnrollmentRecord) -> None:
        self._enrollments[record.id] = record

    def mark_lesson_complete(self, enrollment_id: int, lesson_id: int) -> None:
        key = (enrollment_id, lesson_id)
        if key not in self._progress:
            self._progress[key] = LessonProgressRecord(
                enrollment_id=enrollment_id,
                lesson_id=lesson_id,
            )

    def completed_lesson_ids(self, enrollment_id: int) -> set[int]:
        return {
            lesson_id
            for (eid, lesson_id) in self._progress
            if eid == enrollment_id
        }

    def is_lesson_complete(self, enrollment_id: int, lesson_id: int) -> bool:
        return (enrollment_id, lesson_id) in self._progress
