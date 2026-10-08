from app.core.exceptions import NotFoundError
from app.repositories.note_repository import NoteRepository
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate


class NoteService:
    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def list_notes(
        self,
        *,
        pinned: bool | None = None,
        search: str | None = None,
    ) -> list[NoteRead]:
        return self._repo.list_notes(pinned=pinned, search=search)

    def get_note(self, note_id: int) -> NoteRead:
        note = self._repo.get(note_id)
        if note is None:
            raise NotFoundError("Note", note_id)
        return note

    def create_note(self, payload: NoteCreate) -> NoteRead:
        return self._repo.create(payload)

    def update_note(self, note_id: int, payload: NoteUpdate) -> NoteRead:
        note = self._repo.update(note_id, payload)
        if note is None:
            raise NotFoundError("Note", note_id)
        return note

    def pin_note(self, note_id: int) -> NoteRead:
        note = self._repo.set_pinned(note_id, True)
        if note is None:
            raise NotFoundError("Note", note_id)
        return note

    def unpin_note(self, note_id: int) -> NoteRead:
        note = self._repo.set_pinned(note_id, False)
        if note is None:
            raise NotFoundError("Note", note_id)
        return note

    def delete_note(self, note_id: int) -> NoteRead:
        note = self._repo.delete(note_id)
        if note is None:
            raise NotFoundError("Note", note_id)
        return note
