from app.repositories.entry_repository import get_entry_repository
from app.services.entry_service import EntryService


def get_entry_service() -> EntryService:
    return EntryService(get_entry_repository())
