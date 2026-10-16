"""Who can see a job, who can change it, and which status moves are legal."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRecord, JobRepository
from app.repositories.user_repository import UserRepository
from app.schemas.job import (
    JobCreate,
    JobPage,
    JobRead,
    JobStatus,
    JobUpdate,
    SkillCount,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DRAFT: {JobStatus.PUBLISHED},
    JobStatus.PUBLISHED: {JobStatus.DRAFT, JobStatus.CLOSED},
    JobStatus.CLOSED: {JobStatus.DRAFT},
}


def _can_view(actor: UserRead | None, record: JobRecord) -> bool:
    if record.status is JobStatus.PUBLISHED:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.employer_id


class JobService:
    def __init__(
        self,
        *,
        jobs: JobRepository,
        applications: ApplicationRepository,
        users: UserRepository,
    ) -> None:
        self._jobs = jobs
        self._applications = applications
        self._users = users

    def list_published(
        self,
        *,
        skill: str | None,
        employer_id: int | None,
        work_mode: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> JobPage:
        rows = [
            job
            for job in self._jobs.list_all()
            if job.status is JobStatus.PUBLISHED
            and self._matches(
                job,
                skill=skill,
                employer_id=employer_id,
                work_mode=work_mode,
                query=query,
            )
        ]
        rows.sort(key=lambda job: (job.published_at or job.created_at, job.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def list_mine(
        self,
        actor: UserRead,
        *,
        status: JobStatus | None,
        limit: int,
        offset: int,
    ) -> JobPage:
        rows = [job for job in self._jobs.list_all() if job.employer_id == actor.id]
        if status is not None:
            rows = [job for job in rows if job.status is status]
        rows.sort(key=lambda job: (job.updated_at, job.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def get_job(self, actor: UserRead | None, slug: str) -> JobRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead | None, slug: str) -> JobRecord:
        record = self._jobs.get_by_slug(slug)
        if record is None or not _can_view(actor, record):
            raise NotFoundError("Job", slug)
        return record

    def create_job(self, actor: UserRead, payload: JobCreate) -> JobRead:
        slug = payload.slug or slugify(payload.title)
        if self._jobs.slug_taken(slug):
            raise ConflictError("Another job already uses this slug")
        now = datetime.now(UTC)
        record = self._jobs.add(
            JobRecord(
                id=self._jobs.allocate_id(),
                employer_id=actor.id,
                title=payload.title,
                slug=slug,
                company=payload.company,
                summary=payload.summary,
                description=payload.description,
                location=payload.location,
                work_mode=payload.work_mode,
                employment_type=payload.employment_type,
                salary_min=payload.salary_min,
                salary_max=payload.salary_max,
                status=JobStatus.DRAFT,
                skills=list(payload.skills),
                created_at=now,
                updated_at=now,
                published_at=None,
            )
        )
        return self._to_read(record)

    def update_job(self, actor: UserRead, slug: str, payload: JobUpdate) -> JobRead:
        record = self.visible_record(actor, slug)
        self._require_employer(actor, record, "Only the employer can edit this job")
        changes = payload.model_dump(exclude_unset=True)
        for field in (
            "title",
            "company",
            "summary",
            "description",
            "location",
            "work_mode",
            "employment_type",
            "salary_min",
            "salary_max",
        ):
            if field in changes:
                setattr(record, field, changes[field])
        if "skills" in changes:
            record.skills = list(changes["skills"])
        record.updated_at = datetime.now(UTC)
        self._jobs.save(record)
        return self._to_read(record)

    def publish(self, actor: UserRead, slug: str) -> JobRead:
        record = self.visible_record(actor, slug)
        self._require_employer(actor, record, "Only the employer can publish this job")
        self._move(
            record,
            source=JobStatus.DRAFT,
            target=JobStatus.PUBLISHED,
            message="Only a draft can be published",
        )
        now = datetime.now(UTC)
        record.published_at = now
        record.updated_at = now
        self._jobs.save(record)
        return self._to_read(record)

    def unpublish(self, actor: UserRead, slug: str) -> JobRead:
        record = self.visible_record(actor, slug)
        self._require_employer(actor, record, "Only the employer can unpublish this job")
        self._move(
            record,
            source=JobStatus.PUBLISHED,
            target=JobStatus.DRAFT,
            message="Only a published job can be unpublished",
        )
        record.published_at = None
        record.updated_at = datetime.now(UTC)
        self._jobs.save(record)
        return self._to_read(record)

    def close(self, actor: UserRead, slug: str) -> JobRead:
        record = self.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.employer_id:
            raise ForbiddenError("Only the employer or an admin can close this job")
        self._move(
            record,
            source=JobStatus.PUBLISHED,
            target=JobStatus.CLOSED,
            message="Only a published job can be closed",
        )
        record.updated_at = datetime.now(UTC)
        self._jobs.save(record)
        return self._to_read(record)

    def reopen(self, actor: UserRead, slug: str) -> JobRead:
        record = self.visible_record(actor, slug)
        self._require_employer(actor, record, "Only the employer can reopen this job")
        self._move(
            record,
            source=JobStatus.CLOSED,
            target=JobStatus.DRAFT,
            message="Only a closed job can be reopened",
        )
        record.published_at = None
        record.updated_at = datetime.now(UTC)
        self._jobs.save(record)
        return self._to_read(record)

    def delete_job(self, actor: UserRead, slug: str) -> None:
        record = self.visible_record(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.employer_id:
            raise ForbiddenError("Only the employer or an admin can delete this job")
        self._applications.delete_for_job(record.id)
        self._jobs.delete(record.id)

    def list_skills(self) -> list[SkillCount]:
        counts: dict[str, int] = {}
        for job in self._jobs.list_all():
            if job.status is not JobStatus.PUBLISHED:
                continue
            for skill in job.skills:
                counts[skill] = counts.get(skill, 0) + 1
        return [SkillCount(name=name, job_count=counts[name]) for name in sorted(counts)]

    def _matches(
        self,
        job: JobRecord,
        *,
        skill: str | None,
        employer_id: int | None,
        work_mode: str | None,
        query: str | None,
    ) -> bool:
        if employer_id is not None and job.employer_id != employer_id:
            return False
        if skill is not None and skill.strip().casefold() not in job.skills:
            return False
        if work_mode is not None and job.work_mode.value != work_mode.strip().casefold():
            return False
        if query is not None:
            needle = query.casefold()
            haystack = (
                f"{job.title}\n{job.company}\n{job.summary}\n{job.description}\n{job.location}"
            ).casefold()
            if needle not in haystack:
                return False
        return True

    def _page(self, rows: list[JobRecord], *, limit: int, offset: int) -> JobPage:
        return JobPage(
            items=[self._to_read(job) for job in rows[offset : offset + limit]],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def _to_read(self, record: JobRecord) -> JobRead:
        employer = self._users.get_by_id(record.employer_id)
        return JobRead(
            id=record.id,
            title=record.title,
            slug=record.slug,
            company=record.company,
            summary=record.summary,
            description=record.description,
            location=record.location,
            work_mode=record.work_mode,
            employment_type=record.employment_type,
            salary_min=record.salary_min,
            salary_max=record.salary_max,
            status=record.status,
            skills=list(record.skills),
            employer_id=record.employer_id,
            employer_name=employer.full_name if employer is not None else "Unknown",
            application_count=self._applications.count_for_job(record.id),
            created_at=record.created_at,
            updated_at=record.updated_at,
            published_at=record.published_at,
        )

    def _require_employer(self, actor: UserRead, record: JobRecord, message: str) -> None:
        if actor.id != record.employer_id:
            raise ForbiddenError(message)

    def _move(
        self,
        record: JobRecord,
        *,
        source: JobStatus,
        target: JobStatus,
        message: str,
    ) -> None:
        allowed = _TRANSITIONS[record.status]
        if record.status is not source or target not in allowed:
            raise ConflictError(f"{message}. This job is {record.status.value}")
        record.status = target
