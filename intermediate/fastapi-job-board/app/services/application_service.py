"""Applications follow job visibility, then extra rules for publish state and duplicates."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.application_repository import ApplicationRecord, ApplicationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationPage,
    ApplicationRead,
    ApplicationStatus,
)
from app.schemas.job import JobStatus
from app.schemas.user import UserRead, UserRole
from app.services.job_service import JobService


class ApplicationService:
    def __init__(
        self,
        *,
        jobs: JobService,
        applications: ApplicationRepository,
        users: UserRepository,
    ) -> None:
        self._jobs = jobs
        self._applications = applications
        self._users = users

    def list_for_job(
        self,
        actor: UserRead,
        slug: str,
        *,
        limit: int,
        offset: int,
    ) -> ApplicationPage:
        job = self._jobs.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != job.employer_id:
            raise ForbiddenError("Only the employer or an admin can view applications for this job")
        rows = self._applications.list_for_job(job.id)
        window = rows[offset : offset + limit]
        return ApplicationPage(
            items=[self._to_read(row) for row in window],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def list_mine(self, actor: UserRead, *, limit: int, offset: int) -> ApplicationPage:
        rows = self._applications.list_for_applicant(actor.id)
        window = rows[offset : offset + limit]
        return ApplicationPage(
            items=[self._to_read(row) for row in window],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def apply(self, actor: UserRead, slug: str, payload: ApplicationCreate) -> ApplicationRead:
        job = self._jobs.visible_record(actor, slug)
        if job.status is not JobStatus.PUBLISHED:
            raise ConflictError("Only published jobs accept applications")
        if actor.id == job.employer_id:
            raise ConflictError("You cannot apply to your own job posting")
        existing = self._applications.find_for_job_and_applicant(job.id, actor.id)
        if existing is not None and existing.status is ApplicationStatus.SUBMITTED:
            raise ConflictError("You already applied to this job")
        if existing is not None and existing.status is ApplicationStatus.WITHDRAWN:
            existing.cover_letter = payload.cover_letter
            existing.status = ApplicationStatus.SUBMITTED
            self._applications.save(existing)
            return self._to_read(existing)
        record = self._applications.add(
            ApplicationRecord(
                id=self._applications.allocate_id(),
                job_id=job.id,
                applicant_id=actor.id,
                cover_letter=payload.cover_letter,
                status=ApplicationStatus.SUBMITTED,
                created_at=datetime.now(UTC),
            )
        )
        return self._to_read(record)

    def withdraw(self, actor: UserRead, slug: str, application_id: int) -> ApplicationRead:
        job = self._jobs.visible_record(actor, slug)
        application = self._applications.get(application_id)
        if application is None or application.job_id != job.id:
            raise NotFoundError("Application", application_id)
        if actor.id != application.applicant_id:
            raise ForbiddenError("Only the applicant can withdraw this application")
        if application.status is ApplicationStatus.WITHDRAWN:
            raise ConflictError("Application is already withdrawn")
        application.status = ApplicationStatus.WITHDRAWN
        self._applications.save(application)
        return self._to_read(application)

    def delete_application(self, actor: UserRead, slug: str, application_id: int) -> None:
        job = self._jobs.visible_record(actor, slug)
        application = self._applications.get(application_id)
        if application is None or application.job_id != job.id:
            raise NotFoundError("Application", application_id)
        is_applicant = actor.id == application.applicant_id
        is_employer = actor.id == job.employer_id
        if actor.role is not UserRole.ADMIN and not is_applicant and not is_employer:
            raise ForbiddenError(
                "Only the applicant, the employer, or an admin can delete this application"
            )
        self._applications.delete(application_id)

    def _to_read(self, record: ApplicationRecord) -> ApplicationRead:
        applicant = self._users.get_by_id(record.applicant_id)
        return ApplicationRead(
            id=record.id,
            job_id=record.job_id,
            cover_letter=record.cover_letter,
            status=record.status,
            applicant_id=record.applicant_id,
            applicant_name=applicant.full_name if applicant is not None else "Unknown",
            created_at=record.created_at,
        )
