from functools import lru_cache

from app.repositories.contact_repository import ContactRepository
from app.services.contact_service import ContactService


@lru_cache
def get_contact_repository() -> ContactRepository:
    return ContactRepository()


def get_contact_service() -> ContactService:
    return ContactService(get_contact_repository())
