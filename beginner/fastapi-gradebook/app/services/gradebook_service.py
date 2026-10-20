from app.repositories.gradebook_repository import GradebookRepository
from app.schemas.gradebook import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    EnrollmentCreate,
    EnrollmentRead,
    GradeCategory,
    GradeCreate,
    GradeDeleteResponse,
    GradeRead,
    GradeStatus,
    GradeUpdate,
    StudentCreate,
    StudentDeleteResponse,
    StudentRead,
    StudentReport,
    StudentUpdate,
)


class GradebookService:
    def __init__(self, repo: GradebookRepository) -> None:
        self._repo = repo

    def list_students(self) -> list[StudentRead]:
        return [StudentRead.model_validate(r) for r in self._repo.list_students()]

    def get_student(self, student_id: int) -> StudentRead:
        return StudentRead.model_validate(self._repo.get_student(student_id))

    def create_student(self, payload: StudentCreate) -> StudentRead:
        record = self._repo.create_student(
            student_number=payload.student_number,
            full_name=payload.full_name,
            email=str(payload.email) if payload.email else None,
        )
        return StudentRead.model_validate(record)

    def update_student(self, student_id: int, payload: StudentUpdate) -> StudentRead:
        fields = payload.model_dump(exclude_unset=True)
        email = fields.get("email")
        if email is not None:
            email = str(email)
        record = self._repo.update_student(
            student_id,
            full_name=fields.get("full_name"),
            email=email,
            email_set="email" in fields,
        )
        return StudentRead.model_validate(record)

    def delete_student(self, student_id: int) -> StudentDeleteResponse:
        self._repo.delete_student(student_id)
        return StudentDeleteResponse(id=student_id)

    def student_report(self, student_id: int) -> StudentReport:
        finals = self._repo.final_grades_for_student(student_id)
        if not finals:
            return StudentReport(
                student_id=student_id,
                final_grade_count=0,
                average_percentage=None,
            )
        percentages = [
            round(100.0 * g.points_earned / g.points_possible, 2) for g in finals
        ]
        avg = round(sum(percentages) / len(percentages), 2)
        return StudentReport(
            student_id=student_id,
            final_grade_count=len(finals),
            average_percentage=avg,
        )

    def list_courses(self) -> list[CourseRead]:
        return [CourseRead.model_validate(r) for r in self._repo.list_courses()]

    def get_course(self, course_id: int) -> CourseRead:
        return CourseRead.model_validate(self._repo.get_course(course_id))

    def create_course(self, payload: CourseCreate) -> CourseRead:
        record = self._repo.create_course(
            course_code=payload.course_code,
            title=payload.title,
            term=payload.term,
        )
        return CourseRead.model_validate(record)

    def update_course(self, course_id: int, payload: CourseUpdate) -> CourseRead:
        record = self._repo.update_course(
            course_id,
            title=payload.title,
            term=payload.term,
        )
        return CourseRead.model_validate(record)

    def list_enrollments(self, course_id: int) -> list[EnrollmentRead]:
        rows = self._repo.list_enrollments(course_id)
        return [EnrollmentRead.model_validate(r) for r in rows]

    def enroll(self, course_id: int, payload: EnrollmentCreate) -> EnrollmentRead:
        record = self._repo.enroll(student_id=payload.student_id, course_id=course_id)
        return EnrollmentRead.model_validate(record)

    def list_grades(
        self,
        *,
        course_id: int | None,
        student_id: int | None,
        category: GradeCategory | None,
        status: GradeStatus | None,
        include_draft: bool,
    ) -> list[GradeRead]:
        rows = self._repo.list_grades(
            course_id=course_id,
            student_id=student_id,
            category=category,
            status=status,
            include_draft=include_draft,
        )
        return [GradeRead.model_validate(r) for r in rows]

    def get_grade(self, grade_id: int) -> GradeRead:
        return GradeRead.model_validate(self._repo.get_grade(grade_id))

    def create_grade(self, course_id: int, payload: GradeCreate) -> GradeRead:
        record = self._repo.create_grade(
            course_id=course_id,
            student_id=payload.student_id,
            title=payload.title,
            category=payload.category,
            points_earned=payload.points_earned,
            points_possible=payload.points_possible,
        )
        return GradeRead.model_validate(record)

    def update_grade(self, grade_id: int, payload: GradeUpdate) -> GradeRead:
        record = self._repo.update_grade(
            grade_id,
            title=payload.title,
            category=payload.category,
            points_earned=payload.points_earned,
            points_possible=payload.points_possible,
        )
        return GradeRead.model_validate(record)

    def finalize_grade(self, grade_id: int) -> GradeRead:
        return GradeRead.model_validate(self._repo.finalize_grade(grade_id))

    def reopen_grade(self, grade_id: int) -> GradeRead:
        return GradeRead.model_validate(self._repo.reopen_grade(grade_id))

    def delete_grade(self, grade_id: int) -> GradeDeleteResponse:
        self._repo.delete_grade(grade_id)
        return GradeDeleteResponse(id=grade_id)
