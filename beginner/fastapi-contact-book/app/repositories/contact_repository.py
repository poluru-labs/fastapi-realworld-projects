from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate

_SEED: dict[int, ContactRead] = {
    1: ContactRead(
        id=1,
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="+1-555-0101",
        company="Analytical Engines Ltd",
        notes="Ask about the notes API pattern.",
        favorite=True,
    ),
    2: ContactRead(
        id=2,
        full_name="Grace Hopper",
        email="grace@example.com",
        phone="+1-555-0102",
        company="Compilers Inc",
        notes="",
        favorite=False,
    ),
    3: ContactRead(
        id=3,
        full_name="Lin Phone-only",
        email=None,
        phone="+1-555-0199",
        company="Field ops",
        notes="No email on file.",
        favorite=False,
    ),
}


class ContactRepository:
    """In-memory contacts. A new process starts from the seed data again."""

    def __init__(self) -> None:
        self._contacts = dict(_SEED)
        self._next_id = max(self._contacts.keys(), default=0) + 1

    def list_contacts(
        self,
        *,
        favorite: bool | None = None,
        search: str | None = None,
    ) -> list[ContactRead]:
        items = list(self._contacts.values())
        if favorite is not None:
            items = [contact for contact in items if contact.favorite is favorite]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                items = [
                    contact
                    for contact in items
                    if needle in contact.full_name.casefold()
                    or needle in contact.phone.casefold()
                    or needle in contact.company.casefold()
                    or needle in contact.notes.casefold()
                    or (
                        contact.email is not None and needle in contact.email.casefold()
                    )
                ]
        return sorted(items, key=lambda contact: (not contact.favorite, contact.id))

    def get(self, contact_id: int) -> ContactRead | None:
        return self._contacts.get(contact_id)

    def email_taken(self, email: str, *, except_id: int | None = None) -> bool:
        normalized = email.casefold()
        for contact in self._contacts.values():
            if except_id is not None and contact.id == except_id:
                continue
            if contact.email is not None and contact.email.casefold() == normalized:
                return True
        return False

    def create(self, payload: ContactCreate) -> ContactRead:
        contact = ContactRead(
            id=self._next_id,
            full_name=payload.full_name,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
            company=payload.company,
            notes=payload.notes,
            favorite=payload.favorite,
        )
        self._contacts[self._next_id] = contact
        self._next_id += 1
        return contact

    def update(self, contact_id: int, payload: ContactUpdate) -> ContactRead | None:
        existing = self._contacts.get(contact_id)
        if existing is None:
            return None
        data = existing.model_dump()
        changes = payload.model_dump(exclude_unset=True)
        if "email" in changes:
            email_value = changes["email"]
            if email_value is None or email_value == "":
                data["email"] = None
            else:
                data["email"] = str(email_value)
            del changes["email"]
        data.update(changes)
        contact = ContactRead(**data)
        self._contacts[contact_id] = contact
        return contact

    def set_favorite(self, contact_id: int, favorite: bool) -> ContactRead | None:
        existing = self._contacts.get(contact_id)
        if existing is None:
            return None
        contact = existing.model_copy(update={"favorite": favorite})
        self._contacts[contact_id] = contact
        return contact

    def delete(self, contact_id: int) -> ContactRead | None:
        return self._contacts.pop(contact_id, None)
