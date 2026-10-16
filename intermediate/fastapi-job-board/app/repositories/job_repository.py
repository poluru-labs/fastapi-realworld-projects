from dataclasses import dataclass
from datetime import datetime

from app.schemas.job import EmploymentType, JobStatus, WorkMode


@dataclass
class JobRecord:
    id: int
    employer_id: int
    title: str
    slug: str
    company: str
    summary: str
    description: str
    location: str
    work_mode: WorkMode
    employment_type: EmploymentType
    salary_min: int | None
    salary_max: int | None
    status: JobStatus
    skills: list[str]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


def _seed_jobs() -> dict[int, JobRecord]:
    published_at = datetime.fromisoformat("2026-03-01T15:00:00+00:00")
    drafted_at = datetime.fromisoformat("2026-03-02T15:00:00+00:00")
    return {
        1: JobRecord(
            id=1,
            employer_id=1,
            title="Senior FastAPI Engineer",
            slug="senior-fastapi-engineer",
            company="Acme Labs",
            summary="Build teaching-friendly APIs with clear auth boundaries.",
            description=(
                "You will design REST APIs, write OpenAPI docs, and mentor junior developers. "
                "Published listings are public; drafts stay visible only to the employer."
            ),
            location="Remote (US)",
            work_mode=WorkMode.REMOTE,
            employment_type=EmploymentType.FULL_TIME,
            salary_min=140_000,
            salary_max=175_000,
            status=JobStatus.PUBLISHED,
            skills=["python", "fastapi", "postgres"],
            created_at=published_at,
            updated_at=published_at,
            published_at=published_at,
        ),
        2: JobRecord(
            id=2,
            employer_id=1,
            title="Draft frontend contract",
            slug="draft-frontend-contract",
            company="Acme Labs",
            summary="Not on the public board yet.",
            description="This draft exists so you can see a 404 without a token.",
            location="New York, NY",
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.CONTRACT,
            salary_min=None,
            salary_max=None,
            status=JobStatus.DRAFT,
            skills=["react"],
            created_at=drafted_at,
            updated_at=drafted_at,
            published_at=None,
        ),
    }


class JobRepository:
    """In-memory job postings keyed by id and slug."""

    def __init__(self) -> None:
        self._by_id = dict(_seed_jobs())
        self._by_slug = {job.slug: job for job in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[JobRecord]:
        return list(self._by_id.values())

    def get_by_slug(self, slug: str) -> JobRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str) -> bool:
        return slug in self._by_slug

    def allocate_id(self) -> int:
        job_id = self._next_id
        self._next_id += 1
        return job_id

    def add(self, record: JobRecord) -> JobRecord:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: JobRecord) -> None:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record

    def delete(self, job_id: int) -> None:
        record = self._by_id.pop(job_id, None)
        if record is not None:
            self._by_slug.pop(record.slug, None)
