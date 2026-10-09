from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.contact_repository import ContactRepository
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate


class ContactService:
    def __init__(self, repository: ContactRepository) -> None:
        self._repo = repository

    def list_contacts(
        self,
        *,
        favorite: bool | None = None,
        search: str | None = None,
    ) -> list[ContactRead]:
        return self._repo.list_contacts(favorite=favorite, search=search)

    def get_contact(self, contact_id: int) -> ContactRead:
        contact = self._repo.get(contact_id)
        if contact is None:
            raise NotFoundError("Contact", contact_id)
        return contact

    def create_contact(self, payload: ContactCreate) -> ContactRead:
        if payload.email is not None and self._repo.email_taken(str(payload.email)):
            raise ConflictError("Another contact already uses this email")
        return self._repo.create(payload)

    def update_contact(self, contact_id: int, payload: ContactUpdate) -> ContactRead:
        changes = payload.model_dump(exclude_unset=True)
        if "email" in changes and changes["email"] not in (None, ""):
            email = str(changes["email"])
            if self._repo.email_taken(email, except_id=contact_id):
                raise ConflictError("Another contact already uses this email")
        contact = self._repo.update(contact_id, payload)
        if contact is None:
            raise NotFoundError("Contact", contact_id)
        return contact

    def favorite_contact(self, contact_id: int) -> ContactRead:
        contact = self._repo.set_favorite(contact_id, True)
        if contact is None:
            raise NotFoundError("Contact", contact_id)
        return contact

    def unfavorite_contact(self, contact_id: int) -> ContactRead:
        contact = self._repo.set_favorite(contact_id, False)
        if contact is None:
            raise NotFoundError("Contact", contact_id)
        return contact

    def delete_contact(self, contact_id: int) -> ContactRead:
        contact = self._repo.delete(contact_id)
        if contact is None:
            raise NotFoundError("Contact", contact_id)
        return contact
