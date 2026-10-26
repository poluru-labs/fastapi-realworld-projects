from app.repositories.link_repository import get_link_repository
from app.services.link_service import LinkService


def get_link_service() -> LinkService:
    return LinkService(get_link_repository())
