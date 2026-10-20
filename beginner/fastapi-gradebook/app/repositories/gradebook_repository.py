from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.gradebook import GradeCategory, GradeStatus


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _student_key(number: str) -> str:
    return number.strip().upper()


def _course_key(code: str) -> str:
    return code.strip().upper()


@dataclass
class StudentRecord:
    id: int
    student_number: str
    full_name: str
    email: str | None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class CourseRecord:
    id: int
    course_code: str
    title: str
    term: str
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class EnrollmentRecord:
    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime = field(default_factory=_utcnow)


@dataclass
class GradeRecord:
    id: int
    course_id: int
    student_id: int
    title: str
    category: GradeCategory
    points_earned: float
    points_possible: float
    status: GradeStatus
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


class GradebookRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._students: dict[int, StudentRecord] = {
            1: StudentRecord(
                id=1,
                student_number="STU-001",
                full_name="Alice Nguyen",
                email="alice@school.example",
                created_at=now,
            ),
            2: StudentRecord(
                id=2,
                student_number="STU-002",
                full_name="Bob Patel",
                email="bob@school.example",
                created_at=now,
            ),
        }
        self._courses: dict[int, CourseRecord] = {
            1: CourseRecord(
                id=1,
                course_code="CS101",
                title="Intro to Programming",
                term="Spring 2026",
                created_at=now,
            ),
            2: CourseRecord(
                id=2,
                course_code="MATH200",
                title="Calculus II",
                term="Spring 2026",
                created_at=now,
            ),
        }
        self._enrollments: dict[int, EnrollmentRecord] = {
            1: EnrollmentRecord(id=1, student_id=1, course_id=1, enrolled_at=now),
            2: EnrollmentRecord(id=2, student_id=2, course_id=1, enrolled_at=now),
            3: EnrollmentRecord(id=3, student_id=1, course_id=2, enrolled_at=now),
        }
        self._grades: dict[int, GradeRecord] = {
            1: GradeRecord(
                id=1,
                course_id=1,
                student_id=1,
                title="Midterm exam",
                category=GradeCategory.EXAM,
                points_earned=88.0,
                points_possible=100.0,
                status=GradeStatus.FINAL,
                created_at=now,
                updated_at=now,
            ),
            2: GradeRecord(
                id=2,
                course_id=1,
                student_id=1,
                title="Lab 3",
                category=GradeCategory.HOMEWORK,
                points_earned=9.0,
                points_possible=10.0,
                status=GradeStatus.FINAL,
                created_at=now,
                updated_at=now,
            ),
            3: GradeRecord(
                id=3,
                course_id=1,
                student_id=2,
                title="Lab 3 draft",
                category=GradeCategory.HOMEWORK,
                points_earned=7.0,
                points_possible=10.0,
                status=GradeStatus.DRAFT,
                created_at=now,
                updated_at=now,
            ),
        }
        self._student_number_index = {
            _student_key(s.student_number): s.id for s in self._students.values()
        }
        self._course_code_index = {
            _course_key(c.course_code): c.id for c in self._courses.values()
        }
        self._enrollment_pair_index = {
            (e.student_id, e.course_id): e.id for e in self._enrollments.values()
        }
        self._next_student_id = 3
        self._next_course_id = 3
        self._next_enrollment_id = 4
        self._next_grade_id = 4

    def list_students(self) -> list[StudentRecord]:
        return sorted(self._students.values(), key=lambda s: s.full_name.lower())

    def get_student(self, student_id: int) -> StudentRecord:
        record = self._students.get(student_id)
        if record is None:
            raise NotFoundError("Student", student_id)
        return record

    def create_student(
        self,
        *,
        student_number: str,
        full_name: str,
        email: str | None,
    ) -> StudentRecord:
        key = _student_key(student_number)
        if key in self._student_number_index:
            raise ConflictError("A student with this student_number already exists.")
        record = StudentRecord(
            id=self._next_student_id,
            student_number=key,
            full_name=full_name,
            email=email,
        )
        self._next_student_id += 1
        self._students[record.id] = record
        self._student_number_index[key] = record.id
        return record

    def update_student(
        self,
        student_id: int,
        *,
        full_name: str | None,
        email: str | None,
        email_set: bool = False,
    ) -> StudentRecord:
        record = self.get_student(student_id)
        if full_name is not None:
            record.full_name = full_name
        if email_set:
            record.email = email
        return record

    def delete_student(self, student_id: int) -> None:
        record = self.get_student(student_id)
        self._student_number_index.pop(_student_key(record.student_number), None)
        del self._students[student_id]

    def list_courses(self) -> list[CourseRecord]:
        return sorted(self._courses.values(), key=lambda c: c.course_code)

    def get_course(self, course_id: int) -> CourseRecord:
        record = self._courses.get(course_id)
        if record is None:
            raise NotFoundError("Course", course_id)
        return record

    def create_course(self, *, course_code: str, title: str, term: str) -> CourseRecord:
        key = _course_key(course_code)
        if key in self._course_code_index:
            raise ConflictError("A course with this course_code already exists.")
        record = CourseRecord(
            id=self._next_course_id,
            course_code=key,
            title=title,
            term=term,
        )
        self._next_course_id += 1
        self._courses[record.id] = record
        self._course_code_index[key] = record.id
        return record

    def update_course(
        self,
        course_id: int,
        *,
        title: str | None,
        term: str | None,
    ) -> CourseRecord:
        record = self.get_course(course_id)
        if title is not None:
            record.title = title
        if term is not None:
            record.term = term
        return record

    def list_enrollments(self, course_id: int) -> list[EnrollmentRecord]:
        self.get_course(course_id)
        return [e for e in self._enrollments.values() if e.course_id == course_id]

    def enroll(self, *, student_id: int, course_id: int) -> EnrollmentRecord:
        self.get_student(student_id)
        self.get_course(course_id)
        pair = (student_id, course_id)
        if pair in self._enrollment_pair_index:
            raise ConflictError("Student is already enrolled in this course.")
        record = EnrollmentRecord(
            id=self._next_enrollment_id,
            student_id=student_id,
            course_id=course_id,
        )
        self._next_enrollment_id += 1
        self._enrollments[record.id] = record
        self._enrollment_pair_index[pair] = record.id
        return record

    def require_enrollment(self, *, student_id: int, course_id: int) -> EnrollmentRecord:
        enrollment_id = self._enrollment_pair_index.get((student_id, course_id))
        if enrollment_id is None:
            raise ConflictError("Student is not enrolled in this course.")
        return self._enrollments[enrollment_id]

    def list_grades(
        self,
        *,
        course_id: int | None,
        student_id: int | None,
        category: GradeCategory | None,
        status: GradeStatus | None,
        include_draft: bool,
    ) -> list[GradeRecord]:
        rows = list(self._grades.values())
        if course_id is not None:
            rows = [g for g in rows if g.course_id == course_id]
        if student_id is not None:
            rows = [g for g in rows if g.student_id == student_id]
        if category is not None:
            rows = [g for g in rows if g.category is category]
        if status is not None:
            rows = [g for g in rows if g.status is status]
        elif not include_draft:
            rows = [g for g in rows if g.status is GradeStatus.FINAL]
        rows.sort(key=lambda g: (g.course_id, g.student_id, g.title.lower()))
        return rows

    def get_grade(self, grade_id: int) -> GradeRecord:
        record = self._grades.get(grade_id)
        if record is None:
            raise NotFoundError("Grade", grade_id)
        return record

    def create_grade(
        self,
        *,
        course_id: int,
        student_id: int,
        title: str,
        category: GradeCategory,
        points_earned: float,
        points_possible: float,
    ) -> GradeRecord:
        self.require_enrollment(student_id=student_id, course_id=course_id)
        if points_earned > points_possible:
            raise ConflictError("points_earned cannot exceed points_possible.")
        now = _utcnow()
        record = GradeRecord(
            id=self._next_grade_id,
            course_id=course_id,
            student_id=student_id,
            title=title,
            category=category,
            points_earned=round(points_earned, 2),
            points_possible=round(points_possible, 2),
            status=GradeStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self._next_grade_id += 1
        self._grades[record.id] = record
        return record

    def update_grade(
        self,
        grade_id: int,
        *,
        title: str | None,
        category: GradeCategory | None,
        points_earned: float | None,
        points_possible: float | None,
    ) -> GradeRecord:
        record = self.get_grade(grade_id)
        if record.status is not GradeStatus.DRAFT:
            raise ConflictError("Only draft grades can be edited.")
        if title is not None:
            record.title = title
        if category is not None:
            record.category = category
        if points_earned is not None:
            record.points_earned = round(points_earned, 2)
        if points_possible is not None:
            record.points_possible = round(points_possible, 2)
        if record.points_earned > record.points_possible:
            raise ConflictError("points_earned cannot exceed points_possible.")
        record.updated_at = _utcnow()
        return record

    def finalize_grade(self, grade_id: int) -> GradeRecord:
        record = self.get_grade(grade_id)
        if record.status is GradeStatus.FINAL:
            raise ConflictError("Grade is already final.")
        record.status = GradeStatus.FINAL
        record.updated_at = _utcnow()
        return record

    def reopen_grade(self, grade_id: int) -> GradeRecord:
        record = self.get_grade(grade_id)
        if record.status is GradeStatus.DRAFT:
            raise ConflictError("Grade is already a draft.")
        record.status = GradeStatus.DRAFT
        record.updated_at = _utcnow()
        return record

    def delete_grade(self, grade_id: int) -> None:
        self.get_grade(grade_id)
        del self._grades[grade_id]

    def final_grades_for_student(self, student_id: int) -> list[GradeRecord]:
        self.get_student(student_id)
        return [
            g
            for g in self._grades.values()
            if g.student_id == student_id and g.status is GradeStatus.FINAL
        ]


@lru_cache
def get_gradebook_repository() -> GradebookRepository:
    return GradebookRepository()
