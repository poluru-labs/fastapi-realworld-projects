"""Course catalog, lesson content, and publish workflow."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.course_repository import (
    CourseRecord,
    CourseRepository,
    LessonRecord,
    LessonRepository,
)
from app.repositories.enrollment_repository import EnrollmentRepository
from app.schemas.course import (
    CourseCreate,
    CourseLevel,
    CourseRead,
    CourseStatus,
    CourseUpdate,
    LessonCreate,
    LessonRead,
    LessonStatus,
    LessonUpdate,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_COURSE_TRANSITIONS: dict[CourseStatus, set[CourseStatus]] = {
    CourseStatus.DRAFT: {CourseStatus.PUBLISHED, CourseStatus.ARCHIVED},
    CourseStatus.PUBLISHED: {CourseStatus.DRAFT, CourseStatus.ARCHIVED},
    CourseStatus.ARCHIVED: {CourseStatus.DRAFT},
}


def can_view_course(actor: UserRead | None, course: CourseRecord) -> bool:
    if course.status is CourseStatus.PUBLISHED:
        return True
    if actor is None:
        return False
    return actor.role is UserRole.ADMIN


def can_view_lesson(
    actor: UserRead | None,
    lesson: LessonRecord,
    *,
    enrolled: bool,
) -> bool:
    if lesson.status is LessonStatus.PUBLISHED and enrolled:
        return True
    if actor is not None and actor.role is UserRole.ADMIN:
        return True
    if lesson.status is LessonStatus.PUBLISHED and actor is None:
        return True
    if lesson.status is LessonStatus.PUBLISHED and actor is not None and not enrolled:
        return True
    return False


def can_read_lesson_body(actor: UserRead | None, *, enrolled: bool) -> bool:
    if enrolled:
        return True
    if actor is not None and actor.role is UserRole.ADMIN:
        return True
    return False


class CourseService:
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

    def list_courses(
        self,
        actor: UserRead | None,
        *,
        status: CourseStatus | None,
        level: CourseLevel | None,
    ) -> list[CourseRead]:
        rows = self._courses.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [row for row in rows if row.status is CourseStatus.PUBLISHED]
        elif status is not None:
            rows = [row for row in rows if row.status is status]
        if level is not None:
            rows = [row for row in rows if row.level is level]
        rows.sort(key=lambda row: (row.title.casefold(), row.id))
        return [self._course_read(row) for row in rows]

    def get_course(self, actor: UserRead | None, slug: str) -> CourseRead:
        row = self._require_visible_course(actor, slug)
        return self._course_read(row)

    def create_course(self, actor: UserRead, payload: CourseCreate) -> CourseRead:
        self._require_admin(actor)
        slug = payload.slug or slugify(payload.title)
        if not slug:
            raise ConflictError("Could not derive a slug from the title")
        if self._courses.slug_taken(slug):
            raise ConflictError("Another course already uses this slug")
        now = datetime.now(UTC)
        record = CourseRecord(
            id=self._courses.allocate_id(),
            slug=slug,
            title=payload.title,
            summary=payload.summary,
            level=payload.level,
            status=CourseStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self._courses.add(record)
        return self._course_read(record)

    def update_course(self, actor: UserRead, slug: str, payload: CourseUpdate) -> CourseRead:
        self._require_admin(actor)
        row = self._require_course(slug)
        if row.status is not CourseStatus.DRAFT:
            raise ConflictError("Only draft courses accept content edits")
        changes = payload.model_dump(exclude_unset=True)
        for field in ("title", "summary", "level"):
            if field in changes and changes[field] is not None:
                setattr(row, field, changes[field])
        row.updated_at = datetime.now(UTC)
        self._courses.save(row)
        return self._course_read(row)

    def transition_course(self, actor: UserRead, slug: str, target: CourseStatus) -> CourseRead:
        self._require_admin(actor)
        row = self._require_course(slug)
        allowed = _COURSE_TRANSITIONS.get(row.status, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {row.status.value} to {target.value}")
        row.status = target
        row.updated_at = datetime.now(UTC)
        self._courses.save(row)
        return self._course_read(row)

    def list_lessons(
        self,
        actor: UserRead | None,
        course_slug: str,
    ) -> list[LessonRead]:
        course = self._require_visible_course(actor, course_slug)
        enrolled = self._is_enrolled(actor, course.id)
        rows = self._lessons.list_for_course(course.id)
        visible = [
            lesson
            for lesson in rows
            if can_view_lesson(actor, lesson, enrolled=enrolled)
            and (
                lesson.status is LessonStatus.PUBLISHED
                or (actor is not None and actor.role is UserRole.ADMIN)
            )
        ]
        if actor is None or actor.role is not UserRole.ADMIN:
            visible = [lesson for lesson in visible if lesson.status is LessonStatus.PUBLISHED]
        visible.sort(key=lambda lesson: (lesson.sort_order, lesson.id))
        return [self._lesson_read(course, lesson, actor, enrolled=enrolled) for lesson in visible]

    def get_lesson(self, actor: UserRead | None, course_slug: str, lesson_slug: str) -> LessonRead:
        course = self._require_visible_course(actor, course_slug)
        lesson = self._lessons.get_by_slug(course.id, lesson_slug)
        enrolled = self._is_enrolled(actor, course.id)
        if lesson is None or not can_view_lesson(actor, lesson, enrolled=enrolled):
            raise NotFoundError("Lesson", lesson_slug)
        if actor is None or actor.role is not UserRole.ADMIN:
            if lesson.status is not LessonStatus.PUBLISHED:
                raise NotFoundError("Lesson", lesson_slug)
        return self._lesson_read(course, lesson, actor, enrolled=enrolled)

    def create_lesson(self, actor: UserRead, course_slug: str, payload: LessonCreate) -> LessonRead:
        self._require_admin(actor)
        course = self._require_course(course_slug)
        slug = payload.slug or slugify(payload.title)
        if not slug:
            raise ConflictError("Could not derive a slug from the title")
        if self._lessons.slug_taken(course.id, slug):
            raise ConflictError("Another lesson in this course already uses this slug")
        now = datetime.now(UTC)
        record = LessonRecord(
            id=self._lessons.allocate_id(),
            course_id=course.id,
            slug=slug,
            title=payload.title,
            body=payload.body,
            sort_order=payload.sort_order,
            status=LessonStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self._lessons.add(record)
        return self._lesson_read(course, record, actor, enrolled=True)

    def update_lesson(
        self,
        actor: UserRead,
        course_slug: str,
        lesson_slug: str,
        payload: LessonUpdate,
    ) -> LessonRead:
        self._require_admin(actor)
        course = self._require_course(course_slug)
        lesson = self._require_lesson(course.id, lesson_slug)
        if lesson.status is not LessonStatus.DRAFT:
            raise ConflictError("Only draft lessons accept content edits")
        changes = payload.model_dump(exclude_unset=True)
        for field in ("title", "body", "sort_order"):
            if field in changes and changes[field] is not None:
                setattr(lesson, field, changes[field])
        lesson.updated_at = datetime.now(UTC)
        self._lessons.save(lesson)
        return self._lesson_read(course, lesson, actor, enrolled=True)

    def publish_lesson(self, actor: UserRead, course_slug: str, lesson_slug: str) -> LessonRead:
        return self._lesson_status(actor, course_slug, lesson_slug, LessonStatus.PUBLISHED)

    def unpublish_lesson(self, actor: UserRead, course_slug: str, lesson_slug: str) -> LessonRead:
        return self._lesson_status(actor, course_slug, lesson_slug, LessonStatus.DRAFT)

    def _lesson_status(
        self,
        actor: UserRead,
        course_slug: str,
        lesson_slug: str,
        target: LessonStatus,
    ) -> LessonRead:
        self._require_admin(actor)
        course = self._require_course(course_slug)
        lesson = self._require_lesson(course.id, lesson_slug)
        lesson.status = target
        lesson.updated_at = datetime.now(UTC)
        self._lessons.save(lesson)
        return self._lesson_read(course, lesson, actor, enrolled=True)

    def _is_enrolled(self, actor: UserRead | None, course_id: int) -> bool:
        if actor is None:
            return False
        row = self._enrollments.active_for_user_course(actor.id, course_id)
        return row is not None

    def _published_lesson_count(self, course_id: int) -> int:
        return sum(
            1
            for lesson in self._lessons.list_for_course(course_id)
            if lesson.status is LessonStatus.PUBLISHED
        )

    def _course_read(self, row: CourseRecord) -> CourseRead:
        return CourseRead(
            id=row.id,
            slug=row.slug,
            title=row.title,
            summary=row.summary,
            level=row.level,
            status=row.status,
            published_lesson_count=self._published_lesson_count(row.id),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _lesson_read(
        self,
        course: CourseRecord,
        lesson: LessonRecord,
        actor: UserRead | None,
        *,
        enrolled: bool,
    ) -> LessonRead:
        show_body = can_read_lesson_body(actor, enrolled=enrolled)
        return LessonRead(
            id=lesson.id,
            course_id=course.id,
            course_slug=course.slug,
            slug=lesson.slug,
            title=lesson.title,
            body=lesson.body if show_body else "",
            sort_order=lesson.sort_order,
            status=lesson.status,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )

    def _require_visible_course(self, actor: UserRead | None, slug: str) -> CourseRecord:
        row = self._courses.get_by_slug(slug)
        if row is None or not can_view_course(actor, row):
            raise NotFoundError("Course", slug)
        return row

    def _require_course(self, slug: str) -> CourseRecord:
        row = self._courses.get_by_slug(slug)
        if row is None:
            raise NotFoundError("Course", slug)
        return row

    def _require_lesson(self, course_id: int, slug: str) -> LessonRecord:
        row = self._lessons.get_by_slug(course_id, slug)
        if row is None:
            raise NotFoundError("Lesson", slug)
        return row

    @staticmethod
    def _require_admin(actor: UserRead) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only a platform admin can manage courses")
