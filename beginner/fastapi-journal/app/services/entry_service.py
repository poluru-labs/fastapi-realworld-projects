from datetime import date

from app.core.exceptions import NotFoundError
from app.repositories.entry_repository import EntryRepository
from app.schemas.entry import (
    EntryCreate,
    EntryDeleteResponse,
    EntryRead,
    EntryUpdate,
    TagListResponse,
)


class EntryService:
    def __init__(self, repo: EntryRepository) -> None:
        self._repo = repo

    def list_tags(self) -> TagListResponse:
        return TagListResponse(tags=self._repo.list_tags())

    def list_entries(
        self,
        *,
        tag: str | None,
        mood: str | None,
        search: str | None,
        starred: bool | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[EntryRead]:
        rows = self._repo.list_entries(
            tag=tag,
            mood=mood,
            search=search,
            starred=starred,
            date_from=date_from,
            date_to=date_to,
        )
        return [EntryRead.model_validate(r) for r in rows]

    def get_entry(self, entry_id: int) -> EntryRead:
        return EntryRead.model_validate(self._repo.get(entry_id))

    def get_by_date(self, entry_date: date) -> EntryRead:
        record = self._repo.get_by_date(entry_date)
        if record is None:
            raise NotFoundError("Entry", entry_date.isoformat())
        return EntryRead.model_validate(record)

    def create_entry(self, payload: EntryCreate) -> EntryRead:
        record = self._repo.create(
            entry_date=payload.entry_date,
            title=payload.title,
            body=payload.body,
            mood=payload.mood.value if payload.mood else None,
            tags=payload.tags,
            starred=payload.starred,
        )
        return EntryRead.model_validate(record)

    def update_entry(self, entry_id: int, payload: EntryUpdate) -> EntryRead:
        record = self._repo.get(entry_id)
        if payload.title is not None:
            record.title = payload.title
        if payload.body is not None:
            record.body = payload.body
        if payload.tags is not None:
            record.tags = payload.tags
        if payload.starred is not None:
            record.starred = payload.starred
        if "mood" in payload.model_fields_set:
            record.mood = payload.mood.value if payload.mood is not None else None
        self._repo.mark_updated(record)
        return EntryRead.model_validate(record)

    def star(self, entry_id: int) -> EntryRead:
        return EntryRead.model_validate(self._repo.set_starred(entry_id, starred=True))

    def unstar(self, entry_id: int) -> EntryRead:
        return EntryRead.model_validate(self._repo.set_starred(entry_id, starred=False))

    def delete_entry(self, entry_id: int) -> EntryDeleteResponse:
        self._repo.delete(entry_id)
        return EntryDeleteResponse(id=entry_id)
