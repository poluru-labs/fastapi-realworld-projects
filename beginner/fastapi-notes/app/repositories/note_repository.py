from app.schemas.note import NoteCreate, NoteRead, NoteUpdate

_SEED: dict[int, NoteRead] = {
    1: NoteRead(
        id=1,
        title="Meeting notes",
        body="Discuss the API layout.",
        pinned=True,
    ),
    2: NoteRead(
        id=2,
        title="Grocery list",
        body="Milk and bread",
        pinned=False,
    ),
    3: NoteRead(
        id=3,
        title="FastAPI reading",
        body="Path, query, and body parameters.",
        pinned=False,
    ),
}


class NoteRepository:
    """In-memory notes. A new process starts from the seed data again."""

    def __init__(self) -> None:
        self._notes = dict(_SEED)
        self._next_id = max(self._notes.keys(), default=0) + 1

    def list_notes(
        self,
        *,
        pinned: bool | None = None,
        search: str | None = None,
    ) -> list[NoteRead]:
        items = list(self._notes.values())
        if pinned is not None:
            items = [note for note in items if note.pinned is pinned]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                items = [
                    note
                    for note in items
                    if needle in note.title.casefold() or needle in note.body.casefold()
                ]
        return sorted(items, key=lambda note: (not note.pinned, note.id))

    def get(self, note_id: int) -> NoteRead | None:
        return self._notes.get(note_id)

    def create(self, payload: NoteCreate) -> NoteRead:
        note = NoteRead(id=self._next_id, **payload.model_dump())
        self._notes[self._next_id] = note
        self._next_id += 1
        return note

    def update(self, note_id: int, payload: NoteUpdate) -> NoteRead | None:
        existing = self._notes.get(note_id)
        if existing is None:
            return None
        data = existing.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        note = NoteRead(**data)
        self._notes[note_id] = note
        return note

    def set_pinned(self, note_id: int, pinned: bool) -> NoteRead | None:
        existing = self._notes.get(note_id)
        if existing is None:
            return None
        note = existing.model_copy(update={"pinned": pinned})
        self._notes[note_id] = note
        return note

    def delete(self, note_id: int) -> NoteRead | None:
        return self._notes.pop(note_id, None)
