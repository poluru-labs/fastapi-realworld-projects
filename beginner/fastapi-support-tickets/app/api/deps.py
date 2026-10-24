from app.repositories.ticket_repository import get_ticket_repository
from app.services.ticket_service import TicketService


def get_ticket_service() -> TicketService:
    return TicketService(get_ticket_repository())
