"""Enrollments, lesson completion, and progress tracking."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.course_repository import CourseRepository, LessonRepository
from app.repositories.enrollment_repository import EnrollmentRecord, EnrollmentRepository
from app.schemas.course import (
    CourseStatus,
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentStatus,
    LessonStatus,
)
from app.schemas.user import UserRead, UserRole


class EnrollmentService:
    def __init__(
        self,
        *,
        courses: CourseRepository,
        lessons: LessonRepository,
        enrollments: EnrollmentRepository,
    ) -> None:
        self._courses = courses
        self._lessons = lessons
        self._enrollments = enrollments

    def list_enrollments(
        self,
        actor: UserRead,
        *,
        status: EnrollmentStatus | None,
    ) -> list[EnrollmentRead]:
        if actor.role is UserRole.ADMIN:
            rows = self._enrollments.list_all()
        else:
            rows = self._enrollments.list_for_user(actor.id)
        if status is not None:
            rows = [row for row in rows if row.status is status]
        rows.sort(key=lambda row: (row.enrolled_at, row.id), reverse=True)
        return [self._to_read(row) for row in rows]

    def get_enrollment(self, actor: UserRead, enrollment_id: int) -> EnrollmentRead:
        row = self._require_visible(actor, enrollment_id)
        return self._to_read(row)

    def enroll(self, actor: UserRead, payload: EnrollmentCreate) -> EnrollmentRead:
        course = self._courses.get_by_slug(payload.course_slug)
        if course is None or course.status is not CourseStatus.PUBLISHED:
            raise NotFoundError("Course", payload.course_slug)

        existing = self._enrollments.active_for_user_course(actor.id, course.id)
        if existing is not None:
            raise ConflictError("You are already enrolled in this course")

        record = EnrollmentRecord(
            id=self._enrollments.allocate_id(),
            user_id=actor.id,
            course_id=course.id,
            status=EnrollmentStatus.ACTIVE,
            enrolled_at=datetime.now(UTC),
        )
        self._enrollments.add(record)
        return self._to_read(record)

    def complete_lesson(
        self,
        actor: UserRead,
        enrollment_id: int,
        lesson_slug: str,
    ) -> EnrollmentRead:
        row = self._require_visible(actor, enrollment_id)
        if row.status is not EnrollmentStatus.ACTIVE:
            raise ConflictError("Only active enrollments accept lesson completion")

        lesson = self._lessons.get_by_slug(row.course_id, lesson_slug)
        if lesson is None or lesson.status is not LessonStatus.PUBLISHED:
            raise NotFoundError("Lesson", lesson_slug)

        if not self._enrollments.is_lesson_complete(enrollment_id, lesson.id):
            self._enrollments.mark_lesson_complete(enrollment_id, lesson.id)

        total = self._published_lesson_count(row.course_id)
        done = len(self._enrollments.completed_lesson_ids(enrollment_id))
        if total > 0 and done >= total:
            row.status = EnrollmentStatus.COMPLETED
            row.completed_at = datetime.now(UTC)
            self._enrollments.save(row)

        return self._to_read(row)

    def drop(self, actor: UserRead, enrollment_id: int) -> EnrollmentRead:
        row = self._require_visible(actor, enrollment_id)
        if row.status is not EnrollmentStatus.ACTIVE:
            raise ConflictError("Only active enrollments can be dropped")
        row.status = EnrollmentStatus.DROPPED
        self._enrollments.save(row)
        return self._to_read(row)

    def _published_lesson_count(self, course_id: int) -> int:
        return sum(
            1
            for lesson in self._lessons.list_for_course(course_id)
            if lesson.status is LessonStatus.PUBLISHED
        )

    def _to_read(self, row: EnrollmentRecord) -> EnrollmentRead:
        course = self._courses.get(row.course_id)
        total = self._published_lesson_count(row.course_id)
        done = len(self._enrollments.completed_lesson_ids(row.id))
        percent = int((done / total) * 100) if total else 0
        return EnrollmentRead(
            id=row.id,
            user_id=row.user_id,
            course_id=row.course_id,
            course_slug=course.slug if course else "unknown",
            course_title=course.title if course else "Unknown",
            status=row.status,
            completed_lessons=done,
            total_lessons=total,
            progress_percent=percent,
            enrolled_at=row.enrolled_at,
            completed_at=row.completed_at,
        )

    def _require_visible(self, actor: UserRead, enrollment_id: int) -> EnrollmentRecord:
        row = self._enrollments.get(enrollment_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Enrollment", enrollment_id)
        return row

    @staticmethod
    def _can_view(actor: UserRead, row: EnrollmentRecord) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.user_id == actor.id
