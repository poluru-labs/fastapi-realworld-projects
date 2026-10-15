from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.course import CourseLevel, CourseStatus, LessonStatus


@dataclass
class CourseRecord:
    id: int
    slug: str
    title: str
    summary: str
    level: CourseLevel
    status: CourseStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class LessonRecord:
    id: int
    course_id: int
    slug: str
    title: str
    body: str
    sort_order: int
    status: LessonStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


def _seed_courses() -> dict[int, CourseRecord]:
    return {
        1: CourseRecord(
            id=1,
            slug="fastapi-fundamentals",
            title="FastAPI fundamentals",
            summary="Routes, dependencies, and Pydantic models for HTTP APIs.",
            level=CourseLevel.INTERMEDIATE,
            status=CourseStatus.PUBLISHED,
            created_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
        ),
        2: CourseRecord(
            id=2,
            slug="draft-async-deep-dive",
            title="Async deep dive (draft)",
            summary="Not visible on the public catalog.",
            level=CourseLevel.ADVANCED,
            status=CourseStatus.DRAFT,
            created_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
        ),
    }


def _seed_lessons() -> dict[int, LessonRecord]:
    return {
        1: LessonRecord(
            id=1,
            course_id=1,
            slug="welcome",
            title="Welcome",
            body="What you will build in this course.",
            sort_order=1,
            status=LessonStatus.PUBLISHED,
            created_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
        ),
        2: LessonRecord(
            id=2,
            course_id=1,
            slug="routing-and-deps",
            title="Routing and dependencies",
            body="How FastAPI wires paths to callables and shared dependencies.",
            sort_order=2,
            status=LessonStatus.PUBLISHED,
            created_at=datetime.fromisoformat("2026-09-01T11:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T11:00:00+00:00"),
        ),
        3: LessonRecord(
            id=3,
            course_id=1,
            slug="draft-quiz",
            title="Draft quiz",
            body="Hidden until published.",
            sort_order=3,
            status=LessonStatus.DRAFT,
            created_at=datetime.fromisoformat("2026-09-01T12:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T12:00:00+00:00"),
        ),
    }


class CourseRepository:
    def __init__(self) -> None:
        self._courses = dict(_seed_courses())
        self._by_slug = {course.slug: course for course in self._courses.values()}
        self._next_id = max(self._courses.keys(), default=0) + 1

    def list_all(self) -> list[CourseRecord]:
        return list(self._courses.values())

    def get(self, course_id: int) -> CourseRecord | None:
        return self._courses.get(course_id)

    def get_by_slug(self, slug: str) -> CourseRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str, *, except_id: int | None = None) -> bool:
        existing = self._by_slug.get(slug)
        if existing is None:
            return False
        return existing.id != except_id

    def allocate_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def add(self, record: CourseRecord) -> None:
        self._courses[record.id] = record
        self._by_slug[record.slug] = record

    def save(self, record: CourseRecord) -> None:
        self._courses[record.id] = record
        self._by_slug[record.slug] = record


class LessonRepository:
    def __init__(self) -> None:
        self._lessons = dict(_seed_lessons())
        self._next_id = max(self._lessons.keys(), default=0) + 1

    def list_for_course(self, course_id: int) -> list[LessonRecord]:
        return [lesson for lesson in self._lessons.values() if lesson.course_id == course_id]

    def get(self, lesson_id: int) -> LessonRecord | None:
        return self._lessons.get(lesson_id)

    def get_by_slug(self, course_id: int, slug: str) -> LessonRecord | None:
        for lesson in self._lessons.values():
            if lesson.course_id == course_id and lesson.slug == slug:
                return lesson
        return None

    def slug_taken(self, course_id: int, slug: str, *, except_id: int | None = None) -> bool:
        existing = self.get_by_slug(course_id, slug)
        if existing is None:
            return False
        return existing.id != except_id

    def allocate_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def add(self, record: LessonRecord) -> None:
        self._lessons[record.id] = record

    def save(self, record: LessonRecord) -> None:
        self._lessons[record.id] = record
