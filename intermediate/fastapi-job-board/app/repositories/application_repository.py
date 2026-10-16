from dataclasses import dataclass
from datetime import datetime

from app.schemas.application import ApplicationStatus


@dataclass
class ApplicationRecord:
    id: int
    job_id: int
    applicant_id: int
    cover_letter: str
    status: ApplicationStatus
    created_at: datetime


def _seed_applications() -> dict[int, ApplicationRecord]:
    return {
        1: ApplicationRecord(
            id=1,
            job_id=1,
            applicant_id=1,
            cover_letter="Publish first. Applications on a draft return 409.",
            status=ApplicationStatus.SUBMITTED,
            created_at=datetime.fromisoformat("2026-03-01T16:00:00+00:00"),
        ),
    }


class ApplicationRepository:
    """In-memory job applications. Deleted with their job."""

    def __init__(self) -> None:
        self._applications = dict(_seed_applications())
        self._next_id = max(self._applications.keys(), default=0) + 1

    def list_for_job(self, job_id: int) -> list[ApplicationRecord]:
        rows = [row for row in self._applications.values() if row.job_id == job_id]
        return sorted(rows, key=lambda row: (row.created_at, row.id))

    def list_for_applicant(self, applicant_id: int) -> list[ApplicationRecord]:
        rows = [row for row in self._applications.values() if row.applicant_id == applicant_id]
        return sorted(rows, key=lambda row: (row.created_at, row.id), reverse=True)

    def get(self, application_id: int) -> ApplicationRecord | None:
        return self._applications.get(application_id)

    def find_for_job_and_applicant(
        self,
        job_id: int,
        applicant_id: int,
    ) -> ApplicationRecord | None:
        for row in self._applications.values():
            if row.job_id == job_id and row.applicant_id == applicant_id:
                return row
        return None

    def count_for_job(self, job_id: int) -> int:
        return sum(1 for row in self._applications.values() if row.job_id == job_id)

    def allocate_id(self) -> int:
        application_id = self._next_id
        self._next_id += 1
        return application_id

    def add(self, record: ApplicationRecord) -> ApplicationRecord:
        self._applications[record.id] = record
        return record

    def save(self, record: ApplicationRecord) -> None:
        self._applications[record.id] = record

    def delete(self, application_id: int) -> None:
        self._applications.pop(application_id, None)

    def delete_for_job(self, job_id: int) -> None:
        doomed = [
            application_id
            for application_id, row in self._applications.items()
            if row.job_id == job_id
        ]
        for application_id in doomed:
            del self._applications[application_id]
