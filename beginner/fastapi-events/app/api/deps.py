from app.repositories.event_repository import get_event_repository
from app.services.event_service import EventService


def get_event_service() -> EventService:
    return EventService(get_event_repository())
